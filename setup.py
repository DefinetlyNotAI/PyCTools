import os
import pathlib
import re
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
    except Exception as err:
        sys.exit(
            f"[x] Failed to create output directory: {err}\n"
            "        Suggested action: Ensure you have write permissions in the parent directory.\n"
        )


def print_separator(title: str = None) -> None:
    """Print a separator with an optional title."""
    print("\n" + "=" * 80)
    if title:
        print(title)
        print("=" * 80)


def get_version() -> str:
    try:
        here = os.path.abspath(os.path.dirname(__file__))
        init_path = os.path.join(here, "pyCTools", "__init__.py")
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


if __name__ == "__main__":
    # Begin
    print_separator("SETUP SCRIPT OUTPUT")

    # Get the version from the __init__.py file - manually read
    VERSION = get_version()
    # Check if the bin directory exists and contains the required DLLs
    check_bin_exists(bin_path=os.path.join("pyCTools", "bin"))

    try:
        o_dir = output_dir_init()

        print("\033[90m")
        setup(
            name="pyCTools",
            version=VERSION,
            packages=find_packages() + ["pyCTools.bin.x64", "pyCTools.bin.x86"],
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
        )
        print("\033[0m")

    except Exception as e:
        sys.exit(f"\033[0m[x] An error occurred during setup: {e}\n")

    print_separator()
