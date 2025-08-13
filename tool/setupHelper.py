import os
import pathlib
import re
import shutil
import subprocess
import sys


def get_version() -> str:
    try:
        here = os.path.abspath(os.path.dirname(__file__))
        init_path = os.path.join(here, "..", "pyCTools", "__init__.py")
        version_regex = r'^VERSION\s*=\s*[\'"]([^\'"]*)[\'"]'

        with open(init_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(version_regex, content, re.MULTILINE)
        if match:
            return match.group(1)
        else:
            sys.exit("[x] Could not find VERSION string in pyCTools/__init__.py")
    except Exception as err:
        sys.exit(f"[x] Error reading version from __init__.py: {err}\n")


def success_finale(whl_filename_: str, version_: str):
    # Complete the setup process and provide instructions on what to do next
    print("\033[0m\n[*] Completed setup.py execution.")
    if not os.path.isfile("dist/rawBinaryZipped/bin.zip"):
        print(
            "        Suggested action: Run 'distributionHelper.ps1' to create the distribution package for github releases."
        )
    print(
        "        Suggested action: Execute the following to test in VENV:\n\033[96m"
        "                python -m venv dist/venv_test\n"
        "                dist\\venv_test\\Scripts\\Activate.ps1\n"
        "                python -m pip install --upgrade pip\n"
        f"                pip install dist/wheels/{whl_filename_}\n"
        "                # Do whatever you want here and run any script that uses the library\n"
        "                deactivate\n"
        "                Remove-Item -Recurse -Force dist\\venv_test\n\033[0m"
    )

    print("[*] For local installation, run:")
    print(f"        \033[96mcd ..\033[0m")
    print(f"        \033[96mpython -m pip install dist/wheels/{whl_filename_}\033[0m")
    print("[*] If you place the WHL file on the GitHub releases page, users can download it and install it with:")
    print(
        f"        \033[96mpip install https://github.com/DefinetlyNotAI/PyCTools/releases/download/{version_}/{whl_filename_}\033[0m"
    )
    print(f"        > Assuming the version[{version_}] entered earlier is the exact same as the tag release.\n")


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

    if len(wheel_files) != 1:
        print("[*] Multiple wheel files found - selecting the most recent one\n")
    print(f"[*] Found wheel file successfully\n")
    return wheel_files[0]


def cleanup():
    # Remove ./pyCTools.egg-info/
    egg_info = pathlib.Path('./pyCTools.egg-info')
    if egg_info.exists() and egg_info.is_dir():
        shutil.rmtree(egg_info)
        print('[*] Removed ./pyCTools.egg-info/')

    # Remove ./build/
    build_dir = pathlib.Path('./build')
    if build_dir.exists() and build_dir.is_dir():
        shutil.rmtree(build_dir)
        print('[*] Removed ./build/')

    # Remove ./pyCTools/dist/
    pyctools_dist = pathlib.Path('./pyCTools/dist')
    if pyctools_dist.exists() and pyctools_dist.is_dir():
        shutil.rmtree(pyctools_dist)
        print('[*] Removed ./pyCTools/dist/')

    # Ensure ./dist/wheels/ exists
    dist_dir = pathlib.Path('./dist')
    wheels_dir = dist_dir / 'wheels'
    wheels_dir.mkdir(parents=True, exist_ok=True)

    # Move any .whl files in ./dist to ./dist/wheels/
    for whl_file in dist_dir.glob('*.whl'):
        target = wheels_dir / whl_file.name
        shutil.move(str(whl_file), str(target))
        print(f'[*] Moved {whl_file} to {target}')


if __name__ == "__main__":
    # Change to the script's directory
    os.chdir("..")
    # Start the setup process live
    process = subprocess.Popen(
        [sys.executable, "-m", "build", "--wheel"],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    # Wait for the process to complete, quit if it fails, cleanup either way
    exit_code = process.wait()
    cleanup()
    if exit_code != 0:
        sys.exit(1)

    # Get the latest wheel file
    whl_filename = get_latest_wheel("dist/wheels", "pyctools")
    whl_filename = str(whl_filename).replace("\\", "/")
    # Print success message and instructions
    success_finale(whl_filename_=os.path.basename(str(whl_filename).replace("\\", "/")), version_=get_version())
