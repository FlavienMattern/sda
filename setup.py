from setuptools import setup, find_packages

setup(
    name="sda",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "numpy==1.23.5",
        "scipy==1.13.0",
        "obspy==1.4.0",
        "geopandas==0.12.2",
        "pandas==2.2.2",
        "tqdm==4.66.2",
        "geopy==2.4.1",
        "matplotlib==3.8.4"
    ],
    author="Flavien Mattern",
    description="Tools for seismological data analysis",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
