# Python EPICS Archiver Appliance library

Python package to interact with the [EPICS Archiver Appliance](https://slacmshankar.github.io/epicsarchiver_docs/).

## Quick start

```
>>> from epicsarchiver import ArchiverAppliance
>>> archiver = ArchiverAppliance("archiver-01.example.com")
>>> print(archiver.version)
>>> archiver.get_pv_status(pv='BPM*')
>>> df = archiver.get_data('my:pv', start='2018-07-04 13:00', end=datetime.utcnow())

>>> archiver.archive_pv("my:pv:name")
```


The package also installs a command line tool. It can be used to send a list of PVs to archive (from CSV files).
See https://gitlab.esss.lu.se/ics-infrastructure/epicsarchiver-config for the file format.

```
$ epicsarchiver archive --help
Usage: epicsarchiver archive [OPTIONS] [FILES]...

  Archive all PVs included in the files passed as parameters

Options:
  --period TEXT            Sampling period in seconds to use if not provided
                           in the archive file [default: 1]
  --method [MONITOR|SCAN]  Sampling method to use if not provided in the
                           archive file [default: MONITOR]
  --help                   Show this message and exit.
```


## Installation

py-epicsarchiver can be installed using artifactory PyPI repository:

```
$ pip install py-epicsarchiver -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```



## License

MIT
