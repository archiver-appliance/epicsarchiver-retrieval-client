# Python EPICS Archiver Appliance library

![pipeline status](https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver/badges/master/pipeline.svg)
![code coverage](https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver/badges/master/coverage.svg)


Python package to interact with the [EPICS Archiver Appliance](https://slacmshankar.github.io/epicsarchiver_docs/).

- [Documentation](http://ics-software.pages.esss.lu.se/py-epicsarchiver/index.html)
- [Repository](https://gitlab.esss.lu.se/ics-software/py-epicsarchiver)

## Installation

py-epicsarchiver can be installed using artifactory PyPI repository::

```console
pip install py-epicsarchiver -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```

## Quick start

The package also installs a command line tool. Used to fetch data from the archiver and display in the terminal.

```console
$ epicsarchiver --help
Usage: epicsarchiver [OPTIONS] COMMAND [ARGS]...

  Command line tool for interacting with the archiver.

Options:
  --version            Show the version and exit.
  -h, --hostname TEXT  Achiver Appliance hostname or IP [default: localhost]
  --help               Show this message and exit.

Commands:
  archive    Archive all PVs included in the files passed as parameters.
  get        Print out data from an archiver cluster.
  ioc-check  Print out statistics of a single IOC from an archiver cluster.
  rename     Rename all PVs included in the files passed as parameters.
  stats      Print out statistics from an archiver cluster.
```

To fetch events using the python library:

```python
from epicsarchiver import ArchiverAppliance

archiver = ArchiverAppliance("archiver-01.example.com")
print(archiver.version)
archiver.get_pv_status(pv='BPM*')
archiver_events = archiver.get_events('my:pv', start='2018-07-04 13:00', end=datetime.utcnow())
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
