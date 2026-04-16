"""Tests for date_util — parsing inputs and producing UTC archiver timestamps."""

from __future__ import annotations

import datetime

import pytest
from pytz import UTC, timezone

from epicsarchiver.common.date_util import (
    DateFormatError,
    datetime_from_str,
    format_date,
    set_timezone_utc,
)


class TestDatetimeFromStrStrings:
    """String inputs are parsed into UTC-aware datetimes."""

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
        assert datetime_from_str(value) == expected

    def test_string_with_utc_offset(self) -> None:
        """A string carrying +00:00 is returned as UTC."""
        result = datetime_from_str("2018-07-15T13:00:00+00:00")
        assert result == datetime.datetime(2018, 7, 15, 13, tzinfo=UTC)
        assert result.tzinfo is not None

    def test_string_with_positive_offset_converted_to_utc(self) -> None:
        """A string with +02:00 is converted to UTC (subtracts 2 hours)."""
        result = datetime_from_str("2018-07-15T15:00:00+02:00")
        assert result == datetime.datetime(2018, 7, 15, 13, tzinfo=UTC)

    def test_string_with_negative_offset_converted_to_utc(self) -> None:
        """A string with -05:00 is converted to UTC (adds 5 hours)."""
        result = datetime_from_str("2018-07-15T08:00:00-05:00")
        assert result == datetime.datetime(2018, 7, 15, 13, tzinfo=UTC)

    def test_result_is_utc_aware(self) -> None:
        result = datetime_from_str("2018-07-15 13:00")
        assert result.tzinfo is not None
        assert result.utcoffset() == datetime.timedelta(0)

    def test_invalid_string_raises_date_format_error(self) -> None:
        with pytest.raises(DateFormatError):
            datetime_from_str("not-a-date")

    def test_invalid_string_message_contains_input(self) -> None:
        bad = "20180715T13:00:00"  # unsupported separator combination
        with pytest.raises(DateFormatError, match=bad):
            datetime_from_str(bad)


class TestDatetimeFromStrDatetimes:
    """datetime inputs are normalised to UTC without loss of time information."""

    def test_utc_aware_datetime_unchanged(self) -> None:
        dt = datetime.datetime(2018, 7, 15, 19, 5, tzinfo=UTC)
        assert datetime_from_str(dt) == dt

    def test_naive_datetime_assumed_utc(self) -> None:
        naive = datetime.datetime(2018, 7, 15, 19, 5)  # noqa: DTZ001
        result = datetime_from_str(naive)
        assert result == datetime.datetime(2018, 7, 15, 19, 5, tzinfo=UTC)

    def test_non_utc_aware_datetime_converted_to_utc(self) -> None:
        cest = timezone("Europe/Stockholm")
        # 15:00 CEST = 13:00 UTC
        dt_cest = cest.localize(datetime.datetime(2018, 7, 15, 15, 0, 0))  # noqa: DTZ001
        result = datetime_from_str(dt_cest)
        assert result == datetime.datetime(2018, 7, 15, 13, 0, 0, tzinfo=UTC)

    def test_result_is_utc_aware(self) -> None:
        result = datetime_from_str(datetime.datetime(2018, 7, 15, tzinfo=UTC))
        assert result.tzinfo is not None
        assert result.utcoffset() == datetime.timedelta(0)


class TestFormatDate:
    """format_date always produces an ISO 8601 string ending in 'Z'."""

    def test_utc_aware_formats_correctly(self) -> None:
        dt = datetime.datetime(2018, 7, 4, 13, 0, 0, tzinfo=UTC)
        assert format_date(dt) == "2018-07-04T13:00:00.000000Z"

    def test_naive_treated_as_utc(self) -> None:
        dt = datetime.datetime(2018, 7, 4, 13, 0, 0)  # noqa: DTZ001
        assert format_date(dt) == "2018-07-04T13:00:00.000000Z"

    def test_non_utc_timezone_converted(self) -> None:
        cest = timezone("Europe/Stockholm")
        # 15:00 CEST = 13:00 UTC
        dt = cest.localize(datetime.datetime(2018, 7, 4, 15, 0, 0))  # noqa: DTZ001
        assert format_date(dt) == "2018-07-04T13:00:00.000000Z"

    def test_microseconds_preserved(self) -> None:
        dt = datetime.datetime(2018, 7, 4, 13, 0, 0, 123456, tzinfo=UTC)
        assert format_date(dt) == "2018-07-04T13:00:00.123456Z"

    def test_ends_with_z(self) -> None:
        dt = datetime.datetime(2018, 7, 4, tzinfo=UTC)
        assert format_date(dt).endswith("Z")


class TestInputToArchiverTimestamp:
    """Verify the full pipeline from user input string to archiver URL parameter."""

    @pytest.mark.parametrize(
        ("user_input", "expected_archiver_ts"),
        [
            ("20181121 07:00", "2018-11-21T07:00:00.000000Z"),
            ("2018-07-04 13:00", "2018-07-04T13:00:00.000000Z"),
            ("2018-07-04T14:00", "2018-07-04T14:00:00.000000Z"),
            # timezone-aware string: offset removed, value corrected to UTC
            ("2018-07-04T15:00:00+02:00", "2018-07-04T13:00:00.000000Z"),
        ],
    )
    def test_string_to_archiver_timestamp(
        self, user_input: str, expected_archiver_ts: str
    ) -> None:
        assert format_date(datetime_from_str(user_input)) == expected_archiver_ts


class TestSetTimezoneUtc:
    def test_naive_gets_utc(self) -> None:
        naive = datetime.datetime(2018, 7, 15, 12)  # noqa: DTZ001
        result = set_timezone_utc(naive)
        assert result.tzinfo is not None
        assert result == datetime.datetime(2018, 7, 15, 12, tzinfo=UTC)

    def test_utc_aware_unchanged(self) -> None:
        dt = datetime.datetime(2018, 7, 15, 12, tzinfo=UTC)
        assert set_timezone_utc(dt) == dt

    def test_non_utc_aware_converted(self) -> None:
        cest = timezone("Europe/Stockholm")
        dt = cest.localize(datetime.datetime(2018, 7, 15, 14, 0))  # noqa: DTZ001
        result = set_timezone_utc(dt)
        assert result == datetime.datetime(2018, 7, 15, 12, tzinfo=UTC)
