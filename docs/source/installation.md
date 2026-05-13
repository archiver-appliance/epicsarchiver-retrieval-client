
# Installation

**This package requires Python 3.10 or above.**

## Optional extras

epicsarchiver-retrieval-client has a minimal core (protobuf + pytz) that is sufficient for parsing `.pb` files
and working with `ArchiveEvent` objects directly. Heavy dependencies are opt-in:

| Extra | Installs | Unlocks |
|-------|----------|---------|
| `[polars]` | polars ≥ 1.0 | `get_data()` returning a `polars.DataFrame`; `dataframe_from_events()` |
| `[sync]` | requests ≥ 2 | Synchronous `ArchiverRetrieval` HTTP client |
| `[async]` | aiohttp ≥ 3 | Async `AsyncArchiverRetrieval` HTTP client |
| `[cli]` | click ≥ 8, rich ≥ 13 | `epicsarchiver` command-line tool |
| `[all]` | all of the above | Full functionality |

## Install commands

```console
# Full install — recommended for most users
pip install "epicsarchiver-retrieval-client[all]" -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple

# Core only — parse local .pb files; no HTTP clients, no DataFrames, no CLI
pip install epicsarchiver-retrieval-client -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple

# Sync retrieval with DataFrame output
pip install "epicsarchiver-retrieval-client[polars,sync]" -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple

# Async retrieval with DataFrame output
pip install "epicsarchiver-retrieval-client[polars,async]" -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```

To avoid passing the PyPI repository URL on every command, create a `~/.pip/pip.conf`:

```ini
[global]
index-url = https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple
```

The `pypi-virtual` repository aggregates packages from the local `ics-pypi` repository and the remote
`pypi-remote` that serves as a caching proxy for <https://pypi.python.org>.
