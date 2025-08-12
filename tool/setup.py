# Use python setup.py bdist_wheel
import os
import pathlib
import re
import shutil
import sys

try:
    # noinspection PyUnusedImports
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
    # noinspection PyUnusedImports
    from setuptools import setup, find_packages
    import wheel
except ImportError:
    sys.exit(
        f"[x] Missing required dependencies (either wheel or setuptools)\n"
        "        Suggested action: Run 'compilerHelper.ps1' to generate the DLLs before building."
    )


class bdist_wheel_clean(_bdist_wheel):
    def run(self):
        super().run()
        for path in ("build", "pyCTools.egg-info"):
            if os.path.exists(path):
                shutil.rmtree(path)


def prompt_version() -> str:
    try:
        pattern = re.compile(r"^\d+\.\d+\.\d+(-[A-Za-z0-9]+)?$")
        while True:
            version_ = input("[?] Enter package version (format x.x.x or x.x.x-suffix): ").strip()
            if pattern.match(version_):
                return version_
            else:
                print("[!] Invalid version format. Expected something like 1.0.0 or 1.0.0-beta\n")
    except (KeyboardInterrupt, EOFError):
        sys.exit("\n[!] Version input interrupted. Exiting setup.\n")


def get_latest_wheel(dist_dir: str, package_name: str) -> pathlib.Path:
    dist_path = pathlib.Path(dist_dir)
    pattern = f"{package_name}-*.whl"
    wheel_files = sorted(
        dist_path.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if not wheel_files:
        sys.exit(f"[x] No wheel files matching '{pattern}' found in {dist_dir}??\n")

    if len(wheel_files) == 1:
        print(f"[*] Found wheel file successfully\n")
        return wheel_files[0]

    print("\n[*] Multiple wheel files found:")
    for idx, wf in enumerate(wheel_files, 1):
        print(f"\033[96m[{idx}]\033[0m {wf.name}")
    while True:
        try:
            choice = input("[?] Select the wheel file to use (number): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(wheel_files):
                print(f"[*] Selected wheel file successfully\n")
                return wheel_files[int(choice) - 1]
            else:
                print("[!] Invalid selection. Please enter a valid number.\n")
        except (KeyboardInterrupt, EOFError):
            sys.exit("\n[!] Selection interrupted. Exiting setup.\n")


def success_finale(whl_filename_: str, version_: str):
    # Complete the setup process and provide instructions on what to do next
    print("\033[0m\n[*] Completed setup.py execution.")
    if not os.path.isfile("../dist/bin.zip"):
        print(
            "        Suggested action: Run 'distributionHelper.ps1' to create the distribution package for github releases.")
    print("        Suggested action: Execute the following to test in VENV:\n\033[96m"
          "                cd ..\n"
          "                python -m venv dist/venv_test\n"
          "                dist\\venv_test\\Scripts\\Activate.ps1\n"
          "                python -m pip install --upgrade pip\n"
          f"                pip install dist/libraryWheel/{whl_filename_}\n"
          "                python example/hwrng_example.py\n"
          "                python example/process_inspect_example.py\n"
          "                deactivate\n"
          "                Remove-Item -Recurse -Force dist\\venv_test\n\033[0m")

    print("[*] For local installation, run:")
    print(f"        \033[96mpython -m pip install dist/libraryWheel/{whl_filename_}\033[0m")
    print("[*] If you place the WHL file on the GitHub releases page, users can download it and install it with:")
    print(
        f"        \033[96mpip install https://github.com/DefinetlyNotAI/PyCTools/releases/download/{version_}/{whl_filename_}\033[0m")
    print(f"        > Assuming the version[{version_}] entered earlier is the exact same as the tag release.\n")


def check_bin_exists(bin_path: str):
    try:
        # Check that bin exists and has x86 & x64 DLLs
        if not os.path.isdir(bin_path):
            sys.exit(
                "[x] 'pyCTools/bin/' folder not found.\n"
                "        Suggested action: Run 'compilerHelper.ps1' to generate the DLLs before building.\n"
            )

        # Check subfolders and DLL presence
        for arch in ("x86", "x64"):
            arch_path = os.path.join(bin_path, arch)
            if not os.path.isdir(arch_path) or not any(f.lower().endswith(".dll") for f in os.listdir(arch_path)):
                sys.exit(
                    f"[x] Missing DLLs in pyCTools/bin/{arch}/\n"
                    "        Suggested action: Run 'compilerHelper.ps1' to generate the DLLs before building.\n"
                )
    except Exception as err:
        sys.exit(f"[x] Fatal error while checking files exist and are ready: {err}")


def output_dir_init() -> pathlib.Path:
    try:
        # Ensure ../dist/libraryWheel/ exists
        output_dir = pathlib.Path(__file__).parent.parent / "dist" / "libraryWheel"
        output_dir.mkdir(parents=True, exist_ok=True)

        return output_dir
    except Exception as e:
        sys.exit(f"[x] Failed to create output directory: {e}\n"
                 "        Suggested action: Ensure you have write permissions in the parent directory.\n")


if __name__ == "__main__":
    print("[*] Starting setup.py script for pyCTools...\n")

    # Change to the script's root directory
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    check_bin_exists(bin_path=os.path.join("pyCTools", "bin"))

    try:
        version = prompt_version()
        o_dir = output_dir_init()

        print("\033[90m")
        setup(
            name="pyCTools",
            version=version,
            packages=find_packages(),
            include_package_data=True,
            package_data={
                "pyCTools": ["bin/x86/*.dll", "bin/x64/*.dll"],
            },
            description="Your pyCTools package with bundled DLLs",
            author="Shahm Najeeb",
            author_email="Shahm_Najeeb@outlook.com",
            url="https://github.com/DefinetlyNotAI/PyCTools",
            classifiers=[
                "Programming Language :: Python :: 3",
                "Operating System :: Microsoft :: Windows",
            ],
            options={
                "bdist_wheel": {"dist_dir": str(o_dir)},
                "sdist": {"dist_dir": str(o_dir)},
            },
            cmdclass={"bdist_wheel": bdist_wheel_clean}
        )
        print("\033[0m")

        whl_filename = get_latest_wheel("dist/libraryWheel", "pyctools")
        whl_filename = str(whl_filename).replace("\\", "/")
    except Exception as e:
        sys.exit(f"\033[0m[x] An error occurred during setup: {e}\n")

    success_finale(whl_filename_=whl_filename, version_=version)
