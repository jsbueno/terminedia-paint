# coding: utf-8
from setuptools import setup, find_packages

setup(
    name="terminedia_paint",
    packages=find_packages(),
    version="0.1.0",
    license="LGPLv3+",
    author="João S. O. Bueno",
    author_email="gwidion@gmail.com",
    description="Applicative to draw images interactively on the posix terminal",
    keywords="terminal cmd posix xterm ANSI color",
    url="https://github.com/jsbueno/terminedia-paint",
    project_urls={
        "Source Code": "https://github.com/jsbueno/terminedia-paint",
    },
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    setup_requires=["setuptools_scm"],
    include_package_data=True,
    zip_safe=True,
    test_requires=[],
    install_requires=[
        "terminedia>=0.4.2",
        "pillow>=6.0.0"
    ],
    extras_require={
        "images": ["pillow>=6.0.0"],
        "tests": ["pytest"],
    },
    entry_points="""
        [console_scripts]
        terminedia-paint=terminedia_paint:run
    """,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: PyPy",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Topic :: Artistic Software",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Terminals",
        "Topic :: Terminals :: Terminal Emulators/X Terminals",
    ],
)
