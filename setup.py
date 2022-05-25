import os
import platform
import subprocess
import urllib.request

from setuptools import (
    setup,
)
from setuptools.command.develop import (
    develop,
)
from setuptools.command.install import (
    install,
)
from setuptools.command.sdist import (
    sdist,
)
from wheel.bdist_wheel import (
    bdist_wheel,
)

DARWIN_INCLUDE = (
    "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include/"
)


def install_libc_headers_and(cmdclass):
    def download_fake_libc_include():
        inc = os.path.join("autopxd", "include")
        if os.path.exists(inc):
            if len(os.listdir(inc)) > 1:  # In addition to .DS_Store on macOS -- we expect more files anyway
                return

        repo = "https://github.com/eliben/pycparser"
        commit = "d554122e2a5702daeb68a3714826c1c7df8cbea3"
        url = f"{repo}/archive/{commit}.tar.gz"

        with urllib.request.urlopen(url) as include_data:
            os.makedirs(inc, exist_ok=True)
            with subprocess.Popen(
                ["tar", "xfz", "-", f"-C{inc}", "--strip-components=3", f"pycparser-{commit}/utils/fake_libc_include/"],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as proc:
                _, stderr = proc.communicate(input=include_data.read())
                assert proc.returncode == 0, stderr

    def generate_fake_darwin_include():
        if not os.path.exists(DARWIN_INCLUDE):
            return
        inc = os.path.join("./autopxd", "darwin-include")
        if os.path.exists(inc):
            if not os.path.isdir(inc):
                raise Exception(f'"{inc}" already exists and is not a directory')
            return
        for root, _, files in os.walk(DARWIN_INCLUDE):
            for file in files:
                root = root.replace(DARWIN_INCLUDE, "")
                stub = os.path.join(inc, root, file)
                print(f"Stubbing {stub}")
                try:
                    os.makedirs(os.path.join(inc, root))
                except OSError:
                    # already exists
                    pass
                with open(stub, "w", encoding="utf-8") as stub_f:
                    stub_f.write('#include "_fake_defines.h"\n#include "_fake_typedefs.h"')

    class Sub(cmdclass):
        def run(self):
            download_fake_libc_include()
            if platform.system() == "Darwin":
                generate_fake_darwin_include()
            cmdclass.run(self)

    return Sub


setup(
    cmdclass={
        "develop": install_libc_headers_and(develop),
        "install": install_libc_headers_and(install),
        "sdist": install_libc_headers_and(sdist),
        "bdist_wheel": install_libc_headers_and(bdist_wheel),
    },
)
