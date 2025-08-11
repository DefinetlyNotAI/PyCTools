# Use python setup.py bdist_wheel
import os
import sys
import re
import pathlib
import shutil

try:
    # noinspection PyUnusedImports
    from setuptools import setup, find_packages
    import wheel
except ImportError:
    sys.exit(
        f"[x] Missing required dependencies (either wheel or setuptools)\n"
        "        Suggested action: Run 'compilerHelper.ps1' to generate the DLLs before building."
    )

print("[*] Starting setup.py script for pyCTools...\n")

# Change to the script's root directory
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def prompt_version():
    try:
        pattern = re.compile(r"^\d+\.\d+\.\d+(-[A-Za-z0-9]+)?$")
        while True:
            version_ = input("[?] Enter package version (format x.x.x or x.x.x-suffix): ").strip()
            if pattern.match(version_):
                print("\033[90m")
                return version_
            else:
                print("[!] Invalid version format. Expected something like 1.0.0 or 1.0.0-beta => Trying again...\n")
    except KeyboardInterrupt:
        sys.exit("\n[!] Version input interrupted. Exiting setup.\n")


def get_latest_wheel(dist_dir: str, package_name: str):
    dist_path = pathlib.Path(dist_dir)
    pattern = f"{package_name}-*.whl"
    wheel_files = sorted(
        dist_path.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if not wheel_files:
        sys.exit(f"[x] No wheel files matching '{pattern}' found in {dist_dir}??")
    return wheel_files[0]


# Path to the bin folder inside pyCTools
bin_path = os.path.join("pyCTools", "bin")

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

# Ensure ../dist/pip/ exists
output_dir = pathlib.Path(__file__).parent.parent / "dist" / "pip"
output_dir.mkdir(parents=True, exist_ok=True)

try:
    version = prompt_version()

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
            "bdist_wheel": {"dist_dir": str(output_dir)},
            "sdist": {"dist_dir": str(output_dir)},
        },
    )

    whl_filename = get_latest_wheel("dist/pip", "pyctools")
    whl_filename = str(whl_filename).replace("\\", "/")
except Exception as e:
    sys.exit(f"\033[0m[x] An error occurred during setup: {e}\n")

# Cleanup: remove pyCTools.egg-info and build directories if they exist
for cleanup_dir in ["pyCTools.egg-info", "build", "../pyCTools.egg-info", "../build", "dist"]:
    cleanup_path = pathlib.Path(__file__).parent / cleanup_dir
    if cleanup_path.exists() and cleanup_path.is_dir():
        shutil.rmtree(cleanup_path)
print("\033[90m[*] Completed setup.py script cleanup successfully.\033[0m\n")

print("\033[0m\n[*] Completed setup.py execution.")
if not os.path.isfile("../dist/bin.zip"):
    print(
        "        Suggested action: Run 'distributionHelper.ps1' to create the distribution package for github releases.")
print("        Suggested action: Execute the following to test in VENV:\n\033[96m"
      "                cd ..\n"
      "                python -m venv dist/venv_test\n"
      "                dist\\venv_test\\Scripts\\Activate.ps1\n"
      "                python -m pip install --upgrade pip\n"
      f"                pip install dist/pip/{whl_filename}\n"
      "                python example/hwrng_example.py\n"
      "                python example/process_inspect_example.py\n"
      "                deactivate\n"
      "                Remove-Item -Recurse -Force dist\\venv_test\n\033[0m")


print("[*] For local installation, run:")
print(f"        \033[96mpython -m pip install dist/pip/{whl_filename}\033[0m")
print("[*] If you place the WHL file on the GitHub releases page, users can download it and install it with:")
print(
    f"        \033[96mpip install https://github.com/DefinetlyNotAI/PyCTools/releases/download/{version}/{whl_filename}\033[0m")
print(f"        > Assuming the version[{version}] entered earlier is the same as the tag release.\n")
