# Python EPICS Archiver Appliance library

![pipeline status](https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver/badges/master/pipeline.svg)
![code coverage](https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver/badges/master/coverage.svg)


Python package to interact with the [EPICS Archiver Appliance](https://slacmshankar.github.io/epicsarchiver_docs/).

- [Documentation](http://ics-software.pages.esss.lu.se/py-epicsarchiver/index.html)
- [Repository](https://gitlab.esss.lu.se/ics-software/py-epicsarchiver)

## Installation

py-epicsarchiver can be installed using artifactory PyPI repository:

```console
pip install py-epicsarchiver -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```

The core package has minimal dependencies (protobuf + pytz) and is sufficient for parsing `.pb` files
and working with `ArchiveEvent` objects directly. Heavy dependencies are opt-in via extras:

| Extra | Installs | Use when |
|-------|----------|----------|
| `[polars]` | polars | you want `get_data()` to return a `DataFrame` |
| `[sync]` | requests | you want the synchronous `ArchiverRetrieval` client |
| `[async]` | aiohttp | you want the async `AsyncArchiverRetrieval` client |
| `[cli]` | click, rich | you want the `epicsarchiver` command-line tool |
| `[all]` | everything above | full functionality |

```console
# Everything (recommended for most users)
pip install "py-epicsarchiver[all]" -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple

# Core only — parse local .pb files, no HTTP clients or DataFrames
pip install py-epicsarchiver -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple

# Sync retrieval with DataFrame output
pip install "py-epicsarchiver[polars,sync]" -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```

## Quick start

The package also installs a command line tool. Used to fetch data from the archiver and display in the terminal.

```console
$ epicsarchiver get --help
Usage: epicsarchiver get [OPTIONS] PVS...

  Print out data from an archiver cluster.

  ARGUMENT pvs What pvs to get data of.

  Example usage:

  .. code-block:: console

      epicsarchiver --hostname archiver-01.example.com get PV_NAME1 PV_NAME2

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

To fetch data using the Python library (requires `[polars,sync]`):

```python
from epicsarchiver import ArchiverAppliance
from epicsarchiver.retrieval.archiver_retrieval import ArchiverRetrieval

# High-level: returns a polars DataFrame
retrieval = ArchiverRetrieval("archiver-01.example.com")
df = retrieval.get_data("my:pv", start="2018-07-04 13:00", end="2018-07-04 14:00")
# DataFrame columns: date (ns UTC), val, severity, status, field_values, headers

# Low-level: returns ArchiveEventsData (no polars required)
metadata, events = retrieval.get_events(
    "my:pv",
    start=datetime(2018, 7, 4, 13, 0, tzinfo=UTC),
    end=datetime(2018, 7, 4, 14, 0, tzinfo=UTC),
)
```

To search for PV names:

```python
# Without time range — returns all matching PVs
pv_list = retrieval.search("(?i)^my-system:.*:temperature$")

# With time range — only PVs that recorded data in the given window
pv_list = retrieval.search(
    "(?i)^my-system:.*:temperature$",
    start=datetime(2026, 1, 1, tzinfo=UTC),
    end=datetime(2026, 1, 2, tzinfo=UTC),
)
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
hatch test
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
hatch run types:protoc-gen
```


## License

Distributed under the terms of the [MIT license][license],
