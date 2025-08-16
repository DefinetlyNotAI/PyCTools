# Process Inspection Module (processInspect)

## Overview

The Process Inspection Module provides powerful, low-level access to Windows process metrics and performance data. This library allows applications to monitor process resource usage with minimal overhead, supporting both instantaneous measurements and differential metrics over specified time periods.

## Key Features

- Low-overhead process monitoring
- Memory usage metrics (working set, private bytes, pagefile usage)
- Process resource tracking (handles, threads)
- CPU utilization measurement
- I/O operations monitoring (read/write)
- Support for both snapshot and time-interval measurements
- JSON-formatted output for easy integration
- Customizable metrics selection

## API Reference

### Constants

#### Metrics Flags

The following constants are used to specify which metrics to collect:

```c
#define METRIC_WORKING_SET   0x01  // Process working set size
#define METRIC_PRIVATE_BYTES 0x02  // Private memory usage
#define METRIC_PAGEFILE      0x04  // Pagefile usage
#define METRIC_HANDLES       0x08  // Handle count
#define METRIC_THREADS       0x10  // Thread count
#define METRIC_CPU_USAGE     0x20  // CPU usage percentage
#define METRIC_IO            0x40  // I/O read/write operations
#define METRIC_NET           0x80  // Network usage (when implemented)
```

### Functions

#### `int get_metrics_json(DWORD pid, DWORD metrics, char *json_buf, size_t json_buflen)`

Takes an instantaneous snapshot of the specified process metrics.

**Parameters:**
- `pid`: Process ID to monitor
- `metrics`: Bitwise combination of METRIC_* flags indicating which metrics to collect
- `json_buf`: Output buffer where the JSON-formatted metrics will be written
- `json_buflen`: Size of the output buffer

**Returns:**
- `1` on success
- `0` on failure (invalid process, insufficient permissions, buffer too small)

**JSON Output Format:**
```json
{
  "pid": 1234,
  "working_set_kb": 45678,
  "private_kb": 34567,
  "pagefile_kb": 23456,
  "handles": 345,
  "threads": 12,
  "cpu": 3.45,
  "io_read_kb": 1234,
  "io_write_kb": 5678
}
```

#### `int start_metrics_collection(DWORD pid, DWORD metrics)`

Begins collecting metrics for a process over a time period. Must be paired with a later call to `end_metrics_collection()`.

**Parameters:**
- `pid`: Process ID to monitor
- `metrics`: Bitwise combination of METRIC_* flags indicating which metrics to collect

**Returns:**
- `1` if collection successfully started
- `0` on failure (invalid process, insufficient permissions)

#### `int end_metrics_collection(DWORD pid, DWORD metrics, char *json_buf, size_t json_buflen)`

Ends metrics collection and calculates differentials for the time period since `start_metrics_collection()` was called.

**Parameters:**
- `pid`: Process ID (must match the one used in `start_metrics_collection()`)
- `metrics`: Bitwise combination of METRIC_* flags (must match the ones used in `start_metrics_collection()`)
- `json_buf`: Output buffer where the JSON-formatted metrics will be written
- `json_buflen`: Size of the output buffer

**Returns:**
- `1` on success
- `0` on failure (invalid process, metrics mismatch, insufficient permissions, buffer too small)

**Notes:**
- CPU and I/O metrics are reported as deltas between start and end collection
- Memory metrics are instantaneous values at the time of call

## Usage Examples

### Taking a Snapshot of Process Metrics

```c
#include <windows.h>
#include <stdio.h>

// Import the DLL function
typedef int (*GetMetricsJson_Func)(DWORD, DWORD, char*, size_t);

int main() {
    HMODULE hModule = LoadLibrary("processInspect.dll");
    if (!hModule) {
        printf("Failed to load processInspect.dll\n");
        return 1;
    }
    
    GetMetricsJson_Func GetMetricsJson = 
        (GetMetricsJson_Func)GetProcAddress(hModule, "get_metrics_json");
    
    if (!GetMetricsJson) {
        printf("Failed to get function address\n");
        FreeLibrary(hModule);
        return 1;
    }
    
    const DWORD pid = 1234; // Replace with actual PID
    const DWORD metrics = METRIC_WORKING_SET | METRIC_PRIVATE_BYTES | 
                         METRIC_HANDLES | METRIC_CPU_USAGE;
    
    char json_buffer[1024] = {0};
    
    if (GetMetricsJson(pid, metrics, json_buffer, sizeof(json_buffer))) {
        printf("Process metrics: %s\n", json_buffer);
    } else {
        printf("Failed to get process metrics\n");
    }
    
    FreeLibrary(hModule);
    return 0;
}
```

### Measuring Process Metrics Over Time

```c
#include <windows.h>
#include <stdio.h>

// Import the DLL functions
typedef int (*StartMetricsCollection_Func)(DWORD, DWORD);
typedef int (*EndMetricsCollection_Func)(DWORD, DWORD, char*, size_t);

int main() {
    HMODULE hModule = LoadLibrary("processInspect.dll");
    if (!hModule) {
        printf("Failed to load processInspect.dll\n");
        return 1;
    }
    
    StartMetricsCollection_Func StartMetricsCollection = 
        (StartMetricsCollection_Func)GetProcAddress(hModule, "start_metrics_collection");
    
    EndMetricsCollection_Func EndMetricsCollection = 
        (EndMetricsCollection_Func)GetProcAddress(hModule, "end_metrics_collection");
    
    if (!StartMetricsCollection || !EndMetricsCollection) {
        printf("Failed to get function addresses\n");
        FreeLibrary(hModule);
        return 1;
    }
    
    const DWORD pid = 1234; // Replace with actual PID
    const DWORD metrics = METRIC_CPU_USAGE | METRIC_IO;
    
    if (StartMetricsCollection(pid, metrics)) {
        printf("Started metrics collection. Monitoring for 5 seconds...\n");
        
        // Wait for a period to collect metrics
        Sleep(5000);
        
        char json_buffer[1024] = {0};
        if (EndMetricsCollection(pid, metrics, json_buffer, sizeof(json_buffer))) {
            printf("Process metrics over 5 seconds: %s\n", json_buffer);
        } else {
            printf("Failed to end metrics collection\n");
        }
    } else {
        printf("Failed to start metrics collection\n");
    }
    
    FreeLibrary(hModule);
    return 0;
}
```

### Complete Example with All Metrics

```c
#include <windows.h>
#include <stdio.h>

// Import the DLL functions
typedef int (*StartMetricsCollection_Func)(DWORD, DWORD);
typedef int (*EndMetricsCollection_Func)(DWORD, DWORD, char*, size_t);
typedef int (*GetMetricsJson_Func)(DWORD, DWORD, char*, size_t);

// Metrics flags
#define METRIC_WORKING_SET   0x01
#define METRIC_PRIVATE_BYTES 0x02
#define METRIC_PAGEFILE      0x04
#define METRIC_HANDLES       0x08
#define METRIC_THREADS       0x10
#define METRIC_CPU_USAGE     0x20
#define METRIC_IO            0x40
#define METRIC_NET           0x80

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("Usage: %s <PID>\n", argv[0]);
        return 1;
    }
    
    const DWORD pid = (DWORD)atoi(argv[1]);
    
    HMODULE hModule = LoadLibrary("processInspect.dll");
    if (!hModule) {
        printf("Failed to load processInspect.dll\n");
        return 1;
    }
    
    StartMetricsCollection_Func StartMetricsCollection = 
        (StartMetricsCollection_Func)GetProcAddress(hModule, "start_metrics_collection");
    
    EndMetricsCollection_Func EndMetricsCollection = 
        (EndMetricsCollection_Func)GetProcAddress(hModule, "end_metrics_collection");
    
    GetMetricsJson_Func GetMetricsJson = 
        (GetMetricsJson_Func)GetProcAddress(hModule, "get_metrics_json");
    
    if (!StartMetricsCollection || !EndMetricsCollection || !GetMetricsJson) {
        printf("Failed to get function addresses\n");
        FreeLibrary(hModule);
        return 1;
    }
    
    // All available metrics
    const DWORD all_metrics = METRIC_WORKING_SET | METRIC_PRIVATE_BYTES | 
                             METRIC_PAGEFILE | METRIC_HANDLES | METRIC_THREADS | 
                             METRIC_CPU_USAGE | METRIC_IO;
    
    // First, take an instant snapshot
    char json_buffer[1024] = {0};
    if (GetMetricsJson(pid, all_metrics, json_buffer, sizeof(json_buffer))) {
        printf("Instant metrics snapshot:\n%s\n\n", json_buffer);
    } else {
        printf("Failed to get instant metrics\n");
        FreeLibrary(hModule);
        return 1;
    }
    
    // Then measure over time
    if (StartMetricsCollection(pid, all_metrics)) {
        printf("Collecting metrics for 10 seconds...\n");
        Sleep(10000);
        
        if (EndMetricsCollection(pid, all_metrics, json_buffer, sizeof(json_buffer))) {
            printf("Metrics over 10 seconds:\n%s\n", json_buffer);
        } else {
            printf("Failed to end metrics collection\n");
        }
    } else {
        printf("Failed to start metrics collection\n");
    }
    
    FreeLibrary(hModule);
    return 0;
}
```

## Technical Details

### Process Metrics Explained

#### Memory Metrics

- **Working Set (METRIC_WORKING_SET)**: 
  The set of memory pages currently visible to the process in physical RAM. This includes shared and private pages.

- **Private Bytes (METRIC_PRIVATE_BYTES)**:
  Memory that cannot be shared with other processes. This represents the actual memory cost of the process.

- **Pagefile Usage (METRIC_PAGEFILE)**:
  The amount of the system page file that is being used by the process. This includes all memory that the process has touched, including pages that are in RAM.

#### Resource Metrics

- **Handles (METRIC_HANDLES)**:
  The number of object handles in the process's handle table. This includes files, registry keys, events, etc.

- **Threads (METRIC_THREADS)**:
  The number of threads currently executing in the process.

#### Performance Metrics

- **CPU Usage (METRIC_CPU_USAGE)**:
  Percentage of available CPU time that the process has used. When collected over time, this represents the average usage during that period.

- **I/O Operations (METRIC_IO)**:
  Total bytes read from and written to the disk by the process. When collected over time, this represents the bytes transferred during that period.

### Implementation Details

- The library uses Windows Performance Data Helper (PDH) and Process Status API (PSAPI) to collect metrics
- Thread synchronization is implemented for metric collection over time
- The implementation uses Windows-specific APIs and is optimized for minimal overhead
- CPU usage calculation takes into account all cores/processors in the system
- All memory metrics are reported in kilobytes (KB)

### Known Limitations

- Requires administrator privileges to monitor some processes
- CPU usage metrics may not be 100% accurate for very short-lived processes
- Network metrics are reserved for future implementation (METRIC_NET flag)
- Only supports Windows operating systems

## Building and Integration

### Requirements

- Windows operating system (Windows 7 or later)
- Visual Studio or compatible C compiler
- Required Windows libraries:
  - psapi.lib
  - iphlpapi.lib

### Linking with Your Application

#### Static Linking

```c
#pragma comment(lib, "processInspect.lib")
```

#### Dynamic Loading

```c
HMODULE hModule = LoadLibrary("processInspect.dll");
if (hModule) {
    // Get function pointers using GetProcAddress
    // ...
}
```
