from setuptools import setup, find_packages

setup(
    name="status-dashboard",
    python_requires=">=3.9",
    #url="https://gitlab.ics.muni.cz/perun-proxy-aai/aup-manager",
    description="Module for showing service status",
    packages=find_packages(),
    install_requires=[
        "setuptools",
        "PyYAML~=6.0",
        "flask~=3.0",
        "mysql-connector-python~=8.3",
        "python-dateutil"
    ],
)
