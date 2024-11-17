#!/usr/bin/env python3

import argparse
import os
import platform
import subprocess
import urllib.request

MACOS_SDK_USR_INCLUDE = (
    "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include/"
)

LIBC_STUB_DOWNLOAD_URL = "https://github.com/eliben/pycparser/archive/main.tar.gz"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "autopxd/stubs")


def download_libc_stubs(output_dir):
    inc = os.path.join(output_dir, "include")
    if os.path.exists(inc):
        if len(os.listdir(inc)) > 1:  # In addition to .DS_Store on macOS -- we expect more files anyway
            return

    with urllib.request.urlopen(LIBC_STUB_DOWNLOAD_URL) as include_data:
        os.makedirs(inc, exist_ok=True)
        with subprocess.Popen(
            ["tar", "xfz", "-", f"-C{inc}", "--strip-components=3", "pycparser-main/utils/fake_libc_include/"],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            _, stderr = proc.communicate(input=include_data.read())
            assert proc.returncode == 0, stderr


def generate_macos_stubs(macos_sdk_usr_include_path, output_dir):
    if not os.path.exists(macos_sdk_usr_include_path):
        return
    inc = os.path.join(output_dir, "darwin-include")
    if os.path.exists(inc):
        if not os.path.isdir(inc):
            raise Exception(f'"{inc}" already exists and is not a directory')
        return
    for root, _, files in os.walk(macos_sdk_usr_include_path):
        for file in files:
            root = root.replace(macos_sdk_usr_include_path, "")
            stub = os.path.join(inc, root, file)
            print(f"Stubbing {stub}")
            try:
                os.makedirs(os.path.join(inc, root))
            except OSError:
                # already exists
                pass
            with open(stub, "w", encoding="utf-8") as stub_f:
                stub_f.write('#include "_fake_defines.h"\n#include "_fake_typedefs.h"\n')


def clear_existing_headers(output_dir):
    inc = os.path.join(output_dir, "include")
    if os.path.exists(inc):
        for root, dirs, files in os.walk(inc, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(inc)


def clear_existing_macos_headers(output_dir):
    inc = os.path.join(output_dir, "darwin-include")
    if os.path.exists(inc):
        for root, dirs, files in os.walk(inc, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(inc)


def main():
    parser = argparse.ArgumentParser(
        description="Download libc stub headers and optionally generate macOS stub headers."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for the headers. [default: {DEFAULT_OUTPUT_DIR}]",
    )
    parser.add_argument(
        "--macos-sdk-usr-include-path",
        default=MACOS_SDK_USR_INCLUDE,
        help=f"Path to the macOS SDK /usr/include directory. [default: {MACOS_SDK_USR_INCLUDE}]",
    )
    parser.add_argument(
        "--generate-macos-includes",
        action="store_true",
        default=(platform.system() == "Darwin"),
        help="Generate macOS includes if on macOS. [default: %(default)s]",
    )
    parser.add_argument(
        "--clear-existing-headers",
        action="store_true",
        help="Clear existing headers before downloading or generating new ones.",
    )

    args = parser.parse_args()

    if args.clear_existing_headers:
        clear_existing_headers(args.output_dir)
    download_libc_stubs(args.output_dir)
    if args.generate_macos_includes:
        if args.clear_existing_headers:
            clear_existing_macos_headers(args.output_dir)
        generate_macos_stubs(args.macos_sdk_usr_include_path, args.output_dir)


if __name__ == "__main__":
    main()
