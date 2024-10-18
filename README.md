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
$ epicsarchiver get--help
Usage: epicsarchiver get [OPTIONS] PV

  Print out data from an archiver cluster.

  ARGUMENT pv What pv to get data of.

  Example usage:

  .. code-block:: console

      epicsarchiver --hostname archiver-01.example.com get PV_NAME

Options:
  --debug                         Turn on debug logging
  -s, --start [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S|%Y-%m-%dT%H:%M:%S.%f|%Y-%m-%d %H:%M:%S.%f]
                                  Start time of query [default: 30 seconds
                                  ago]
  -e, --end [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S|%Y-%m-%dT%H:%M:%S.%f|%Y-%m-%d %H:%M:%S.%f]
                                  End time of query, [default: now]
  -p, --processor-name [FIRSTSAMPLE|LASTSAMPLE|FIRSTFILL|LASTFILL|MEAN|MIN|MAX|COUNT|NCOUNT|NTH|MEDIAN|STD|JITTER|IGNOREFLYERS|FLYERS|VARIANCE|POPVARIANCE|KURTOSIS|SKEWNESS|LINEAR|LOESS|OPTIMIZED|OPTIMLASTSAMPLE|CAPLOTBINNING|DEADBAND|ERRORBAR]
                                  PreProcessor to use
                                  
                                  Docs at https://epicsarchiver.readthedocs.io/en/latest/user/userguide.html#processing-of-data
  -b, --bin_size INTEGER          Bin size (mostly in seconds) for
                                  preprocessor.
  --help                          Show this message and exit.
```

Note you can also specify a hostname for the archiver either with an environment variable:

```console
export EPICSARCHIVER_HOSTNAME=archiver-01.example.com 
````

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
