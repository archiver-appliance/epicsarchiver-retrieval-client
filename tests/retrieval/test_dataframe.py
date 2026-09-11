import polars as pl
from polars.testing import assert_frame_equal

from epicsarchiver.retrieval.archive_event import (
    ArchiveEvent,
    ArchiveEventsMeta,
    FieldValue,
)
from epicsarchiver.retrieval.dataframe import dataframe_from_events


def test_dataframe_from_events_preserves_nested_field_values() -> None:
    events = [
        ArchiveEvent(
            pv="pv:first",
            val=1,
            secondsintoyear=1,
            year=2024,
            nanos=0,
            severity=2,
            status=3,
            field_values=[FieldValue("units", "A")],
        ),
        ArchiveEvent(
            pv="pv:second",
            val=2,
            secondsintoyear=2,
            year=2025,
            nanos=0,
            severity=4,
            status=5,
            field_values=None,
        ),
    ]
    metadata = {
        2024: ArchiveEventsMeta(
            pv_name="pv:first",
            pv_type="scalar",
            element_count=1,
            headers=[FieldValue("precision", "3")],
            year=2024,
        )
    }

    dataframe = dataframe_from_events(events, metadata)

    field_value_dtype = pl.List(pl.Struct({"name": pl.Utf8, "value": pl.Utf8}))
    expected = pl.DataFrame({
        "field_values": pl.Series(
            [[{"name": "units", "value": "A"}], []], dtype=field_value_dtype
        ),
        "headers": pl.Series(
            [[{"name": "precision", "value": "3"}], []], dtype=field_value_dtype
        ),
    })
    assert_frame_equal(
        dataframe.select("field_values", "headers"),
        expected,
    )
