## `setup.py`

from setuptools import setup, find_packages
import ezan.version

setup(
    name="ezan",
    version=ezan.version.__version__,
    author="Mehmet Keçeci",
    author_email="mkececi@yaani.com",
    description="Namaz vakitleri ve kıble hesaplama aracı",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/WhiteSymmetry/ezan",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: AGPL-3.0-or-later License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=[
        "astropy>=7.2.0",
        "pytz>=2025.2",
        "requests>=2.32.5",
    ],
)