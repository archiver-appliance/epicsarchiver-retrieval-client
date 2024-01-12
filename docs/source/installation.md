
# Installation

**This package requires Python 3.10 or above.**

py-epicsarchiver can be installed using artifactory PyPI repository

```console
pip install py-epicsarchiver -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```

To avoid having to pass the PyPI repository url in the command line, you can create the following `~/.pip/pip.conf` file

```
[global]
index-url = https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```

The pypi-virtual repository aggregates packages from the local ics-pypi repository and the remote pypi-remote that serves
as a caching proxy for <https://pypi.python.org>.
