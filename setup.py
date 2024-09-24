from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    def run_tests(self):
        import pytest
        errno = pytest.main([])
        exit(errno)

setup(
    name="peerjs_py",
    version="0.1.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "aiortc>=1.9.0,<2.0.0",
        "pyee>=12.0.0,<13.0.0",
        "aiohttp>=3.7.4,<4.0.0",
        "requests>=2.25.1,<3.0.0",
        # "websockets>=9.1,<10.0",
    ],
    author="Mansu Kim",
    author_email="mkim@sellpath",
    description="A Python implementation of PeerJS",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/sellpath/peerjs_py",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    include_package_data=True,
    license="MIT",
    keywords="peerjs webrtc networking",
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
)