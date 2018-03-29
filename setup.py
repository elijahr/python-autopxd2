import os.path
import subprocess

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.sdist import sdist


def install_libc_headers_and(cmdclass):
    def download_fake_libc_include():
        inc = os.path.join('autopxd', 'include')
        if os.path.exists(inc):
            if not os.path.isdir(inc):
                raise Exception(
                    '"{0}" already exists and is not a directory'.format(inc))
            return
        repo = 'https://github.com/eliben/pycparser' 
        commit = 'a47b919287a33dea55cc02b2f8c5f4be2ee8613c'
        url = '{0}/archive/{1}.tar.gz'.format(repo, commit)
        subprocess.check_call((
            'mkdir {0} && cd {0} && '
            'curl -L -o - {1} | '
            'tar xfz - --strip-components=3 '
            'pycparser-{2}/utils/fake_libc_include/'
        ).format(inc, url, commit), shell=True)

    class Sub(cmdclass):
        def run(self):
            download_fake_libc_include()
            cmdclass.run(self)

    return Sub


VERSION = '1.1.2'
REPO    = 'http://github.com/tarruda/python-autopxd'


setup(
    name='autopxd',
    version=VERSION,
    description='Automatically generate Cython pxd files from C headers',
    packages=['autopxd'],
    package_data={'autopxd': ['include/*.h', 'include/**/*.h']},
    author='Thiago de Arruda',
    author_email='tpadilha84@gmail.com',
    url=REPO,
    download_url='{0}/archive/{1}.tar.gz'.format(REPO, VERSION),
    license='MIT',
    cmdclass={
        'develop': install_libc_headers_and(develop),
        'install': install_libc_headers_and(install),
        'sdist': install_libc_headers_and(sdist)
    },
    install_requires=[
        'six',
        'Click',
        'pycparser',
    ],
    entry_points='''
    [console_scripts]
    autopxd=autopxd:cli
    ''',
    )
