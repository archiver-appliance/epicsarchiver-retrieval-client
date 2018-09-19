# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("CHANGELOG.rst") as changelog_file:
    changelog = changelog_file.read()

requirements = ["requests", "pandas", "python-dateutil", "Click>=6.0"]

test_requirements = ["pytest", "pytest-cov", "responses", "pytest-mock"]

setup(
    name="py-epicsarchiver",
    author="Benjamin Bertrand",
    author_email="benjamin.bertrand@esss.se",
    description="Python package to interact with the EPICS Archiver Appliance",
    long_description=readme + "\n\n" + changelog,
    url="https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver",
    license="MIT license",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    install_requires=requirements,
    test_suite="tests",
    tests_require=test_requirements,
    include_package_data=True,
    packages=find_packages(include=["epicsarchiver"]),
    keywords="epicsarchiver",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    entry_points={"console_scripts": ["epicsarchiver=epicsarchiver.command:cli"]},
)
