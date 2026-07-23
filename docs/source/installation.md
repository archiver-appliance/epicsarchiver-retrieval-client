
# Installation

**This package requires Python 3.10 or above.**

## Optional extras

epicsarchiver-retrieval-client has a small core (httpx + protobuf + pytz) that provides both the
synchronous `ArchiverRetrieval` and async `AsyncArchiverRetrieval` HTTP clients, and is sufficient for
parsing `.pb` files and working with `ArchiveEvent` objects directly. Heavy dependencies are opt-in:

| Extra | Installs | Unlocks |
|-------|----------|---------|
| `[polars]` | polars ≥ 1.0 | `get_data()` returning a `polars.DataFrame`; `dataframe_from_events()` |
| `[cli]` | click ≥ 8, rich ≥ 13 | `epicsarchiver` command-line tool |
| `[all]` | all of the above | Full functionality |

## Install commands

```console
# Full install — recommended for most users
pip install "epicsarchiver-retrieval-client[all]"

# Core only — retrieval clients and .pb parsing; no DataFrames, no CLI
pip install epicsarchiver-retrieval-client

# Retrieval with DataFrame output
pip install "epicsarchiver-retrieval-client[polars]"
```
