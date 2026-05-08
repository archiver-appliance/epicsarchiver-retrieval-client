"""Tests for date_util — parsing inputs and producing UTC archiver timestamps."""

from __future__ import annotations

import datetime

import pytest
from pytz import UTC, timezone

from epicsarchiver.common.date_util import (
    DateFormatError,
    QueryTimestamp,
    ResponseTimestamp,
    ensure_utc,
)


class TestFromInputStrings:
    """String inputs are parsed into QueryTimestamps."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(
                "20180715",
                datetime.datetime(2018, 7, 15, tzinfo=UTC),
                id="compact-date",
            ),
            pytest.param(
                "20180715 17:45",
                datetime.datetime(2018, 7, 15, 17, 45, tzinfo=UTC),
                id="compact-datetime-hm",
            ),
            pytest.param(
                "20180715 17:45:30",
                datetime.datetime(2018, 7, 15, 17, 45, 30, tzinfo=UTC),
                id="compact-datetime-hms",
            ),
            pytest.param(
                "2018-07-15",
                datetime.datetime(2018, 7, 15, tzinfo=UTC),
                id="iso-date",
            ),
            pytest.param(
                "2018-07-15T13:00",
                datetime.datetime(2018, 7, 15, 13, tzinfo=UTC),
                id="iso-T-hm",
            ),
            pytest.param(
                "2018-07-15T13:00:00",
                datetime.datetime(2018, 7, 15, 13, 0, 0, tzinfo=UTC),
                id="iso-T-hms",
            ),
            pytest.param(
                "2018-07-15T13:00:00.123456",
                datetime.datetime(2018, 7, 15, 13, 0, 0, 123456, tzinfo=UTC),
                id="iso-T-microseconds",
            ),
            pytest.param(
                "2018-07-15 13:00",
                datetime.datetime(2018, 7, 15, 13, tzinfo=UTC),
                id="iso-space-hm",
            ),
            pytest.param(
                "2018-07-15 13:00:00",
                datetime.datetime(2018, 7, 15, 13, 0, 0, tzinfo=UTC),
                id="iso-space-hms",
            ),
            pytest.param(
                "2018-07-15 13:00:00.123456",
                datetime.datetime(2018, 7, 15, 13, 0, 0, 123456, tzinfo=UTC),
                id="iso-space-microseconds",
            ),
        ],
    )
    def test_naive_strings_treated_as_utc(
        self, value: str, expected: datetime.datetime
    ) -> None:
        assert QueryTimestamp.from_input(value).datetime == expected

    def test_string_with_utc_offset(self) -> None:
        """A string carrying +00:00 is returned as UTC."""
        ts = QueryTimestamp.from_input("2018-07-15T13:00:00+00:00")
        assert ts.datetime == datetime.datetime(2018, 7, 15, 13, tzinfo=UTC)
        assert ts.datetime.tzinfo is not None

    def test_string_with_positive_offset_converted_to_utc(self) -> None:
        """A string with +02:00 is converted to UTC."""
        ts = QueryTimestamp.from_input("2018-07-15T15:00:00+02:00")
        assert ts.datetime == datetime.datetime(2018, 7, 15, 13, tzinfo=UTC)

    def test_string_with_negative_offset_converted_to_utc(self) -> None:
        """A string with -05:00 is converted to UTC."""
        ts = QueryTimestamp.from_input("2018-07-15T08:00:00-05:00")
        assert ts.datetime == datetime.datetime(2018, 7, 15, 13, tzinfo=UTC)

    def test_result_is_utc_aware(self) -> None:
        ts = QueryTimestamp.from_input("2018-07-15 13:00")
        assert ts.datetime.tzinfo is not None
        assert ts.datetime.utcoffset() == datetime.timedelta(0)

    def test_invalid_string_raises_date_format_error(self) -> None:
        with pytest.raises(DateFormatError):
            QueryTimestamp.from_input("not-a-date")

    def test_invalid_string_message_contains_input(self) -> None:
        bad = "20180715T13:00:00"
        with pytest.raises(DateFormatError, match=bad):
            QueryTimestamp.from_input(bad)


class TestFromInputDatetimes:
    """datetime inputs are normalised to UTC."""

    def test_utc_aware_datetime_unchanged(self) -> None:
        dt = datetime.datetime(2018, 7, 15, 19, 5, tzinfo=UTC)
        assert QueryTimestamp.from_input(dt).datetime == dt

    def test_naive_datetime_assumed_utc(self) -> None:
        naive = datetime.datetime(2018, 7, 15, 19, 5)  # noqa: DTZ001
        result = QueryTimestamp.from_input(naive).datetime
        assert result == datetime.datetime(2018, 7, 15, 19, 5, tzinfo=UTC)

    def test_non_utc_aware_datetime_converted_to_utc(self) -> None:
        cest = timezone("Europe/Stockholm")
        dt_cest = cest.localize(
            datetime.datetime(2018, 7, 15, 15, 0, 0),  # noqa: DTZ001
        )
        result = QueryTimestamp.from_input(dt_cest).datetime
        assert result == datetime.datetime(2018, 7, 15, 13, 0, 0, tzinfo=UTC)

    def test_result_is_utc_aware(self) -> None:
        result = QueryTimestamp.from_input(
            datetime.datetime(2018, 7, 15, tzinfo=UTC)
        ).datetime
        assert result.tzinfo is not None
        assert result.utcoffset() == datetime.timedelta(0)


class TestToQueryString:
    def test_utc_aware_formats_correctly(self) -> None:
        dt = datetime.datetime(2018, 7, 4, 13, 0, 0, tzinfo=UTC)
        assert (
            QueryTimestamp.from_datetime(dt).to_query_string()
            == "2018-07-04T13:00:00.000000Z"
        )

    def test_naive_treated_as_utc(self) -> None:
        dt = datetime.datetime(2018, 7, 4, 13, 0, 0)  # noqa: DTZ001
        assert (
            QueryTimestamp.from_datetime(dt).to_query_string()
            == "2018-07-04T13:00:00.000000Z"
        )

    def test_non_utc_timezone_converted(self) -> None:
        cest = timezone("Europe/Stockholm")
        dt = cest.localize(
            datetime.datetime(2018, 7, 4, 15, 0, 0),  # noqa: DTZ001
        )
        assert (
            QueryTimestamp.from_datetime(dt).to_query_string()
            == "2018-07-04T13:00:00.000000Z"
        )

    def test_microseconds_preserved(self) -> None:
        dt = datetime.datetime(2018, 7, 4, 13, 0, 0, 123456, tzinfo=UTC)
        assert (
            QueryTimestamp.from_datetime(dt).to_query_string()
            == "2018-07-04T13:00:00.123456Z"
        )

    def test_ends_with_z(self) -> None:
        dt = datetime.datetime(2018, 7, 4, tzinfo=UTC)
        result = QueryTimestamp.from_datetime(dt).to_query_string()
        assert result.endswith("Z")


class TestInputToQueryString:
    """Full pipeline from user input to archiver URL parameter."""

    @pytest.mark.parametrize(
        ("user_input", "expected_archiver_ts"),
        [
            ("20181121 07:00", "2018-11-21T07:00:00.000000Z"),
            ("2018-07-04 13:00", "2018-07-04T13:00:00.000000Z"),
            ("2018-07-04T14:00", "2018-07-04T14:00:00.000000Z"),
            (
                "2018-07-04T15:00:00+02:00",
                "2018-07-04T13:00:00.000000Z",
            ),
        ],
    )
    def test_string_to_archiver_timestamp(
        self, user_input: str, expected_archiver_ts: str
    ) -> None:
        assert (
            QueryTimestamp.from_input(user_input).to_query_string()
            == expected_archiver_ts
        )


class TestEnsureUtc:
    def test_naive_gets_utc(self) -> None:
        naive = datetime.datetime(2018, 7, 15, 12)  # noqa: DTZ001
        result = ensure_utc(naive)
        assert result.tzinfo is not None
        assert result == datetime.datetime(2018, 7, 15, 12, tzinfo=UTC)

    def test_utc_aware_unchanged(self) -> None:
        dt = datetime.datetime(2018, 7, 15, 12, tzinfo=UTC)
        assert ensure_utc(dt) == dt

    def test_non_utc_aware_converted(self) -> None:
        cest = timezone("Europe/Stockholm")
        dt = cest.localize(
            datetime.datetime(2018, 7, 15, 14, 0),  # noqa: DTZ001
        )
        result = ensure_utc(dt)
        assert result == datetime.datetime(2018, 7, 15, 12, tzinfo=UTC)


class TestResponseTimestamp:
    """ResponseTimestamp preserves nanosecond precision."""

    def test_ns_property_preserves_full_precision(self) -> None:
        ts = ResponseTimestamp(1_531_663_200_123_456_789)
        assert ts.ns == 1_531_663_200_123_456_789

    def test_datetime_truncates_to_microseconds(self) -> None:
        ts = ResponseTimestamp(1_531_663_200_123_456_789)
        assert ts.datetime.microsecond == 123456

    def test_from_yearsecondnanos_preserves_nanos(self) -> None:
        ts = ResponseTimestamp.from_yearsecondnanos(2018, 100, 500)
        expected_ns = (1514764800 + 100) * 1_000_000_000 + 500
        assert ts.ns == expected_ns

    def test_datetime_is_utc_aware(self) -> None:
        ts = ResponseTimestamp(1_531_663_200_000_000_000)
        assert ts.datetime.tzinfo is not None
        assert ts.datetime.utcoffset() == datetime.timedelta(0)
