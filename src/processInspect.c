#include <windows.h>
#include <psapi.h>
#include <tlhelp32.h>
#include <iphlpapi.h>
#include <stdio.h>
#include <string.h>

#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "iphlpapi.lib")

#define METRIC_WORKING_SET   0x01
#define METRIC_PRIVATE_BYTES 0x02
#define METRIC_PAGEFILE      0x04
#define METRIC_HANDLES       0x08
#define METRIC_THREADS       0x10
#define METRIC_CPU_USAGE     0x20
#define METRIC_IO            0x40
#define METRIC_NET           0x80

typedef struct {
    DWORD pid;
    DWORD metrics;
    FILETIME sysKernelStart, sysUserStart;
    FILETIME procKernelStart, procUserStart;
    IO_COUNTERS ioStart;
    int active;
} MetricsSession;

// Structure for the monitoring thread
typedef struct {
    DWORD pid;
    DWORD metrics;
    DWORD intervalMs;
    int totalDurationMs;   // -1 means run until explicitly stopped
    int isRunning;
    HANDLE threadHandle;
    void (*callbackFn)(const char*, void*);
    void* userData;
} MonitoringContext;

static MetricsSession g_session = {0};
static MonitoringContext g_monitorContext = {0};

static ULONGLONG fileTimeToInt(const FILETIME ft) {
    ULARGE_INTEGER ui;
    ui.LowPart = ft.dwLowDateTime;
    ui.HighPart = ft.dwHighDateTime;
    return ui.QuadPart;
}

// ReSharper disable once CppParameterMayBeConst
double get_cpu_usage(HANDLE hProcess) {
    static FILETIME lastSysKernel = {0}, lastSysUser = {0};
    static ULONGLONG lastProcKernel = 0, lastProcUser = 0;

    FILETIME sysIdle, sysKernel, sysUser;
    FILETIME procCreation, procExit, procKernel, procUser;

    if (!GetSystemTimes(&sysIdle, &sysKernel, &sysUser)) return 0.0;
    if (!GetProcessTimes(hProcess, &procCreation, &procExit, &procKernel, &procUser)) return 0.0;

    const ULONGLONG sysKernelInt = fileTimeToInt(sysKernel);
    const ULONGLONG sysUserInt = fileTimeToInt(sysUser);
    const ULONGLONG procKernelInt = fileTimeToInt(procKernel);
    const ULONGLONG procUserInt = fileTimeToInt(procUser);

    const ULONGLONG sysDelta = (sysKernelInt + sysUserInt) - (fileTimeToInt(lastSysKernel) + fileTimeToInt(lastSysUser));
    const ULONGLONG procDelta = (procKernelInt + procUserInt) - (lastProcKernel + lastProcUser);

    lastSysKernel = sysKernel;
    lastSysUser = sysUser;
    lastProcKernel = procKernelInt;
    lastProcUser = procUserInt;

    if (sysDelta == 0) return 0.0;
    return ((double)procDelta / (double)sysDelta) * 100.0;
}

void build_metrics_json(char *buf, const size_t buflen, const DWORD pid, const DWORD metrics,
                        const size_t ws, const size_t priv, const size_t pf, const DWORD handles, const DWORD threads,
                        const double cpu, const unsigned long long io_r, const unsigned long long io_w) {
    int n = 0;
    n += snprintf(buf + n, buflen - n, "{");
    n += snprintf(buf + n, buflen - n, "\"pid\":%lu", pid);
    if (metrics & METRIC_WORKING_SET)
        n += snprintf(buf + n, buflen - n, ",\"working_set_kb\":%zu", ws);
    if (metrics & METRIC_PRIVATE_BYTES)
        n += snprintf(buf + n, buflen - n, ",\"private_kb\":%zu", priv);
    if (metrics & METRIC_PAGEFILE)
        n += snprintf(buf + n, buflen - n, ",\"pagefile_kb\":%zu", pf);
    if (metrics & METRIC_HANDLES)
        n += snprintf(buf + n, buflen - n, ",\"handles\":%lu", handles);
    if (metrics & METRIC_THREADS)
        n += snprintf(buf + n, buflen - n, ",\"threads\":%lu", threads);
    if (metrics & METRIC_CPU_USAGE)
        n += snprintf(buf + n, buflen - n, ",\"cpu\":%.2f", cpu);
    if (metrics & METRIC_IO)
        n += snprintf(buf + n, buflen - n, ",\"io_read_kb\":%llu,\"io_write_kb\":%llu", io_r, io_w);
    snprintf(buf + n, buflen - n, "}");
}

static int capture_start_state(const DWORD pid, const DWORD metrics, MetricsSession *session) {
    // ReSharper disable once CppLocalVariableMayBeConst
    HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (!hProcess) return 0;

    FILETIME sysIdle, sysKernel, sysUser;
    FILETIME procCreation, procExit, procKernel, procUser;
    IO_COUNTERS ioCounters = {0};

    if (metrics & METRIC_CPU_USAGE) {
        if (!GetSystemTimes(&sysIdle, &sysKernel, &sysUser)) {
            CloseHandle(hProcess);
            return 0;
        }
        if (!GetProcessTimes(hProcess, &procCreation, &procExit, &procKernel, &procUser)) {
            CloseHandle(hProcess);
            return 0;
        }
        session->sysKernelStart = sysKernel;
        session->sysUserStart = sysUser;
        session->procKernelStart = procKernel;
        session->procUserStart = procUser;
    }
    if (metrics & METRIC_IO) {
        GetProcessIoCounters(hProcess, &ioCounters);
        session->ioStart = ioCounters;
    }
    session->pid = pid;
    session->metrics = metrics;
    session->active = 1;
    CloseHandle(hProcess);
    return 1;
}

__declspec(dllexport)
int start_metrics_collection(const DWORD pid, const DWORD metrics) {
    memset(&g_session, 0, sizeof(g_session));
    return capture_start_state(pid, metrics, &g_session);
}

__declspec(dllexport)
int end_metrics_collection(const DWORD pid, const DWORD metrics, char *json_buf, const size_t json_buflen) {
    if (!g_session.active || g_session.pid != pid || g_session.metrics != metrics) return 0;
    if (!json_buf || json_buflen == 0) return 0;

    // ReSharper disable once CppLocalVariableMayBeConst
    HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (!hProcess) return 0;

    PROCESS_MEMORY_COUNTERS_EX pmc = {0};
    if (!GetProcessMemoryInfo(hProcess, (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc))) {
        CloseHandle(hProcess);
        return 0;
    }

    DWORD handleCount = 0;
    GetProcessHandleCount(hProcess, &handleCount);

    DWORD threadCount = 0;
    PROCESSENTRY32 pe32 = {0};
    pe32.dwSize = sizeof(PROCESSENTRY32);
    // ReSharper disable once CppLocalVariableMayBeConst
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap != INVALID_HANDLE_VALUE) {
        if (Process32First(hSnap, &pe32)) {
            do {
                if (pe32.th32ProcessID == pid) {
                    threadCount = pe32.cntThreads;
                    break;
                }
            } while (Process32Next(hSnap, &pe32));
        }
        CloseHandle(hSnap);
    }

    IO_COUNTERS ioCounters = {0};
    GetProcessIoCounters(hProcess, &ioCounters);

    // Calculate deltas for CPU and IO
    double cpu = 0.0;
    if (metrics & METRIC_CPU_USAGE) {
        FILETIME sysIdle, sysKernel, sysUser;
        FILETIME procCreation, procExit, procKernel, procUser;
        GetSystemTimes(&sysIdle, &sysKernel, &sysUser);
        GetProcessTimes(hProcess, &procCreation, &procExit, &procKernel, &procUser);

        const ULONGLONG sysStart = fileTimeToInt(g_session.sysKernelStart) + fileTimeToInt(g_session.sysUserStart);
        const ULONGLONG sysEnd = fileTimeToInt(sysKernel) + fileTimeToInt(sysUser);
        const ULONGLONG procStart = fileTimeToInt(g_session.procKernelStart) + fileTimeToInt(g_session.procUserStart);
        const ULONGLONG procEnd = fileTimeToInt(procKernel) + fileTimeToInt(procUser);

        const ULONGLONG sysDelta = sysEnd - sysStart;
        const ULONGLONG procDelta = procEnd - procStart;
        if (sysDelta != 0)
            cpu = ((double)procDelta / (double)sysDelta) * 100.0;
    }

    unsigned long long io_r = 0, io_w = 0;
    if (metrics & METRIC_IO) {
        io_r = (ioCounters.ReadTransferCount - g_session.ioStart.ReadTransferCount) / 1024;
        io_w = (ioCounters.WriteTransferCount - g_session.ioStart.WriteTransferCount) / 1024;
    }

    const size_t ws = pmc.WorkingSetSize / 1024;
    const size_t priv = pmc.PrivateUsage / 1024;
    const size_t pf = pmc.PagefileUsage / 1024;

    build_metrics_json(json_buf, json_buflen, pid, metrics, ws, priv, pf, handleCount, threadCount, cpu, io_r, io_w);

    CloseHandle(hProcess);
    g_session.active = 0;
    return 1;
}

__declspec(dllexport)
int get_metrics_json(const DWORD pid, const DWORD metrics, char *json_buf, const size_t json_buflen) {
    if (!json_buf || json_buflen == 0) return 0;

    // ReSharper disable once CppLocalVariableMayBeConst
    HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (!hProcess) return 0;

    PROCESS_MEMORY_COUNTERS_EX pmc = {0};
    if (!GetProcessMemoryInfo(hProcess, (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc))) {
        CloseHandle(hProcess);
        return 0;
    }

    DWORD handleCount = 0;
    GetProcessHandleCount(hProcess, &handleCount);

    DWORD threadCount = 0;
    PROCESSENTRY32 pe32 = {0};
    pe32.dwSize = sizeof(PROCESSENTRY32);
    // ReSharper disable once CppLocalVariableMayBeConst
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap != INVALID_HANDLE_VALUE) {
        if (Process32First(hSnap, &pe32)) {
            do {
                if (pe32.th32ProcessID == pid) {
                    threadCount = pe32.cntThreads;
                    break;
                }
            } while (Process32Next(hSnap, &pe32));
        }
        CloseHandle(hSnap);
    }

    IO_COUNTERS ioCounters = {0};
    GetProcessIoCounters(hProcess, &ioCounters);

    const size_t ws = pmc.WorkingSetSize / 1024;
    const size_t priv = pmc.PrivateUsage / 1024;
    const size_t pf = pmc.PagefileUsage / 1024;
    const double cpu = get_cpu_usage(hProcess);
    const unsigned long long io_r = ioCounters.ReadTransferCount / 1024;
    const unsigned long long io_w = ioCounters.WriteTransferCount / 1024;

    build_metrics_json(json_buf, json_buflen, pid, metrics, ws, priv, pf, handleCount, threadCount, cpu, io_r, io_w);

    CloseHandle(hProcess);
    return 1;
}

// Thread function to collect metrics at regular intervals
// ReSharper disable once CppParameterMayBeConst
DWORD WINAPI MonitoringThreadProc(LPVOID lpParam) {
    MonitoringContext* ctx = (MonitoringContext*)lpParam;
    const DWORD startTime = GetTickCount();
    char buffer[2048];  // Buffer for JSON metrics

    while (ctx->isRunning) {
        // Collect and send metrics
        if (get_metrics_json(ctx->pid, ctx->metrics, buffer, sizeof(buffer))) {
            if (ctx->callbackFn) {
                ctx->callbackFn(buffer, ctx->userData);
            }
        }

        // Check if we need to stop based on duration
        if (ctx->totalDurationMs > 0) {
            const DWORD currentTime = GetTickCount();
            if (currentTime - startTime >= (DWORD)ctx->totalDurationMs) {
                break;
            }
        }

        // Sleep for the interval period
        Sleep(ctx->intervalMs);
    }

    ctx->isRunning = 0;
    return 0;
}

__declspec(dllexport)
int start_metrics_monitoring(
    const DWORD pid,
    const DWORD metrics,
    const DWORD intervalMs,
    const int totalDurationMs,
    void (*callbackFn)(const char*, void*),
    void* userData) {

    // Don't start if already running
    if (g_monitorContext.isRunning) {
        return 0;
    }

    // Setup monitoring context
    g_monitorContext.pid = pid;
    g_monitorContext.metrics = metrics;
    g_monitorContext.intervalMs = intervalMs;
    g_monitorContext.totalDurationMs = totalDurationMs;
    g_monitorContext.isRunning = 1;
    g_monitorContext.callbackFn = callbackFn;
    g_monitorContext.userData = userData;

    // Create the monitoring thread
    g_monitorContext.threadHandle = CreateThread(
        NULL,
        0,
        MonitoringThreadProc,
        &g_monitorContext,
        0,
        NULL
    );

    if (g_monitorContext.threadHandle == NULL) {
        g_monitorContext.isRunning = 0;
        return 0;
    }

    return 1;
}

__declspec(dllexport)
int stop_metrics_monitoring() {
    if (!g_monitorContext.isRunning) {
        return 0;
    }

    // Signal the thread to stop
    g_monitorContext.isRunning = 0;

    // Wait for the thread to exit
    if (g_monitorContext.threadHandle != NULL) {
        WaitForSingleObject(g_monitorContext.threadHandle, 5000);  // Wait up to 5 seconds
        CloseHandle(g_monitorContext.threadHandle);
        g_monitorContext.threadHandle = NULL;
    }

    return 1;
}

__declspec(dllexport)
int is_metrics_monitoring_active() {
    return g_monitorContext.isRunning;
}
