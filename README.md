# Python EPICS Archiver Appliance library

Python package to interact with the [EPICS Archiver Appliance](https://slacmshankar.github.io/epicsarchiver_docs/).

## Quick start

```
>>> from epicsarchiver import ArchiverAppliance
>>> archiver = ArchiverAppliance("archiver-01.example.com")
>>> print(archiver.version)
>>> archiver.get_pv_status(pv='BPM*')
>>> df = archiver.get_data('my:pv', start='2018-07-04 13:00', end=datetime.utcnow())
```


## Installation

py-epicsarchiver can be installed using artifactory PyPI repository:

```
$ pip install py-epicsarchiver -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```



## License

MIT
