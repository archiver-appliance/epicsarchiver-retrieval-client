
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
pip install "epicsarchiver-retrieval-client[all]"

# Core only — parse local .pb files; no HTTP clients, no DataFrames, no CLI
pip install epicsarchiver-retrieval-client

# Sync retrieval with DataFrame output
pip install "epicsarchiver-retrieval-client[polars,sync]"

# Async retrieval with DataFrame output
pip install "epicsarchiver-retrieval-client[polars,async]"
```
