# Python EPICS Archiver Appliance library

![black status](https://img.shields.io/badge/code%20style-black-000000.svg)
![pipeline status](https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver/badges/master/pipeline.svg)
![code coverage](https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver/badges/master/coverage.svg)


Python package to interact with the [EPICS Archiver Appliance](https://slacmshankar.github.io/epicsarchiver_docs/).

- [Documentation](http://ics-software.pages.esss.lu.se/py-epicsarchiver/index.html)
- [Repository](https://gitlab.esss.lu.se/ics-software/py-epicsarchiver)

## Quick start

```python
from epicsarchiver import ArchiverAppliance

archiver = ArchiverAppliance("archiver-01.example.com")
print(archiver.version)
archiver.get_pv_status(pv='BPM*')
archiver_events = archiver.get_events('my:pv', start='2018-07-04 13:00', end=datetime.utcnow())
```

The package also installs a command line tool. It can be used to send a list of PVs to archive (from CSV files).
See <https://gitlab.esss.lu.se/ics-infrastructure/epicsarchiver-config> for the file format.

```console
$ epicsarchiver --help

Usage: epicsarchiver [OPTIONS] COMMAND [ARGS]...

  Command line tool for interacting with the archiver.

Options:
  --version        Show the version and exit.
  --hostname TEXT  Achiver Appliance hostname or IP [default: localhost]
  --help           Show this message and exit.

Commands:
  archive  Archive all PVs included in the files passed as parameters.
  rename   Rename all PVs included in the files passed as parameters.
  stats    Print out statistics from an archiver cluster.
```

## Installation

py-epicsarchiver can be installed using artifactory PyPI repository::

```console
pip install py-epicsarchiver -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```
## Development

The package is built and packaged with [Hatch](https://hatch.pypa.io/latest/).

```console
pip install hatch
```

Run all checks and code coverage:

```console
hatch run all
```

Run tests:

```console
hatch run test
```

Run formatting and check:

```console
hatch fmt
```

Run local docs:

```console
hatch run docs:live
```

Regenerate protobuf python api:

```console
hatch run protoc-gen
```


## License

Distributed under the terms of the [MIT license][license],
