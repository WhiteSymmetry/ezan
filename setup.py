# -*- coding: utf-8 -*-
## `setup.py`

from setuptools import setup, find_packages
import io
import re
import sys
import os

# UTF-8 encoding sorunlarını çöz
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_version():
    with open('ezan/__init__.py', 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", content, re.M)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version string.")

setup(
    name="ezan",
    version=get_version(),
    author="Mehmet Keçeci",
    author_email="mkececi@yaani.com",
    description="Namaz vakitleri ve kıble hesaplama aracı",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/WhiteSymmetry/ezan",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=[
        "astropy>=7.2.0",
        "pytz>=2025.2",
        "requests>=2.32.5",
    ],
)