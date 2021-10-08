import os
import platform
import subprocess

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
            if not os.path.isdir(inc):
                raise Exception('"{0}" already exists and is not a directory'.format(inc))
            return
        repo = "https://github.com/eliben/pycparser"
        commit = "d554122e2a5702daeb68a3714826c1c7df8cbea3"
        url = "{0}/archive/{1}.tar.gz".format(repo, commit)
        subprocess.check_call(
            (
                "mkdir {0} && cd {0} && "
                "curl -L -o - {1} | "
                "tar xfz - --strip-components=3 "
                "pycparser-{2}/utils/fake_libc_include/"
            ).format(inc, url, commit),
            shell=True,
        )

    def generate_fake_darwin_include():
        if not os.path.exists(DARWIN_INCLUDE):
            return
        inc = os.path.join("./autopxd", "darwin-include")
        if os.path.exists(inc):
            if not os.path.isdir(inc):
                raise Exception('"{0}" already exists and is not a directory'.format(inc))
            return
        for root, _, files in os.walk(DARWIN_INCLUDE):
            for file in files:
                root = root.replace(DARWIN_INCLUDE, "")
                stub = os.path.join(inc, root, file)
                print("Stubbing %s" % stub)
                try:
                    os.makedirs(os.path.join(inc, root))
                except OSError:
                    # already exists
                    pass
                with open(stub, "w") as stub_f:
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
