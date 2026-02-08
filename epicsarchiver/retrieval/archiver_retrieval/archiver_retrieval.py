"""Archiver Retrieval methods."""

from __future__ import annotations

import datetime
import itertools
import logging
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from pytz import UTC

from epicsarchiver.common.base_archiver import BaseArchiverAppliance
from epicsarchiver.common.date_util import datetime_from_str, format_date
from epicsarchiver.common.validation import (
    validate_processor,
    validate_pv,
    validate_start_end,
)
from epicsarchiver.retrieval.archive_event import ArchiveEvent, dataframe_from_events
from epicsarchiver.retrieval.pb import parse_pb_data

if TYPE_CHECKING:
    from requests import Response

    from epicsarchiver.retrieval.archiver_retrieval.processor import Processor


LOG: logging.Logger = logging.getLogger(__name__)

ENDPOINT_GET_DATA = "/data/getData.raw"
ENDPOINT_GET_MATCHING_PVS = "/bpl/getMatchingPVs"


def json_to_dataframe(data: Any) -> pd.DataFrame:
    """Converts json from the archiver.

    Converts to a dataframe with two
    columns "date" and "val" and the index is "date".

    Args:
        data: json from a json archiver request

    Returns:
        pd.DataFrame
    """
    events_dataframe = pd.DataFrame(data[0]["data"])
    try:
        total_nanos = (
            events_dataframe["secs"].multiply(1e9).add(events_dataframe["nanos"])
        )
        events_dataframe["date"] = pd.to_datetime(total_nanos, unit="ns", utc=True)
    except KeyError:
        # Empty data
        pass
    else:
        events_dataframe = events_dataframe[["date", "val"]]
        events_dataframe = events_dataframe.set_index("date")
    return events_dataframe


class ArchiverRetrieval(BaseArchiverAppliance):
    """Retrieval EPICS Archiver Appliance client.

    Hold a session to the Retrieval Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname [default: localhost]
        port: EPICS Archiver Appliance management port [default: 17665]

    Examples:

    .. code-block:: python

        from epicsarchiver.archiver.retrieval import ArchiverRetrieval

        archappl = ArchiverRetrieval("archiver-01.tn.esss.lu.se")
        print(archappl.version)
        df = archappl.get_data("my:pv", start="2018-07-04 13:00", end=datetime.utcnow())
    """

    def data_retrieval_url(self) -> str:
        """EPICS Archiver Appliance data retrieval url.

        Raises:
            ConnectionError: Raises if archiver not available

        Returns:
            str: url of retrieval engine
        """
        if self._data_retrieval_url is None:
            self._data_retrieval_url = self.info.get("dataRetrievalURL")
            if self._data_retrieval_url is None:
                raise ConnectionError
        return self._data_retrieval_url

    def get_data_url(self) -> str:
        """EPICS Archiver Appliance data retrieval URL.

        Returns:
            str: URL of retrieval engine
        """
        return self.data_retrieval_url() + ENDPOINT_GET_DATA

    def get_matching_pvs_url(self) -> str:
        """Get the EPICS Archiver Appliance matching PVs URL.

        Returns:
            str: URL of matching PVs endoint.
        """
        return self.data_retrieval_url() + ENDPOINT_GET_MATCHING_PVS

    def _get_data_raw(
        self,
        pv: str,
        start: datetime.datetime,
        end: datetime.datetime,
    ) -> Response:
        """Retrieve archived data.

        Args:
            pv: name of the pv.
            start: start time. Can be a string or `datetime.datetime`
                object.
            end: end time. Can be a string or `datetime.datetime`
                object.

        Returns:
            `Response`
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        params = {
            "pv": pv,
            "from": format_date(start),
            "to": format_date(end),
        }
        return self._get(
            self.get_data_url(),
            params=params,
            stream=True,
        )

    def _get_matching_pvs(
        self,
        pv: str,
        limit: int,
    ) -> list[str]:
        """Retrieve list of matching pv names for given glob search string.

        Args:
            pv (str): PV glob name search string.
            limit (int): Limit of PV names to return.

        Returns:
            list[str]: List of pv names
        """
        params = {
            # Simple conversion of glob patterns to regex, case insensitive, anchor
            # beginning and end.
            "regex": "(?i)^" + pv.replace("*", ".*").replace("?", ".") + "$",
            "limit": str(limit),
        }
        return cast(
            "list[str]",
            self._get(
                self.get_matching_pvs_url(),
                params=params,
                stream=True,
            ).json(),
        )

    def get_events(
        self,
        pv: str,
        start: datetime.datetime,
        end: datetime.datetime,
        processor: Processor | None = None,
    ) -> list[ArchiveEvent]:
        """Retrieve archived data.

        Args:
            pv: name of the pv.
            start: start time. Can be a string or `datetime.datetime`
                object.
            end: end time. Can be a string or `datetime.datetime`
                object.
            processor (Processor | None, optional): Preprocessor
                to use. Defaults to None.


        Returns:
            list[ArchiveEvent]: requested events from the archiver.
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        validate_pv(pv)
        validate_start_end(start, end)
        validate_processor(processor)
        pv_request = processor.calc_pv_name(pv) if processor else pv
        r = self._get_data_raw(pv_request, start, end)
        pb_data = r.content
        metadata, events = parse_pb_data(pb_data)
        LOG.debug("Metadata: %s", metadata)
        return events

    def get_data(
        self,
        pv: str,
        start: str | datetime.datetime,
        end: str | datetime.datetime,
        processor: Processor | None = None,
    ) -> pd.DataFrame:
        """Retrieve archived data.

        Args:
            pv: name of the pv.
            start: start time. Can be a string or `datetime.datetime`
                object.
            end: end time. Can be a string or `datetime.datetime`
                object.
            processor (Processor | None, optional): Preprocessor
                to use. Defaults to None.

        Returns:
            `pandas.DataFrame`
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        start_time = datetime_from_str(start)
        end_time = datetime_from_str(end)
        events = self.get_events(pv, start_time, end_time, processor)
        if not events:
            return dataframe_from_events([])
        # Convert events to DataFrame
        return dataframe_from_events(events)

    def search(
        self,
        pvstrings: str | list[str],
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        limit: int = 500,
    ) -> list[str]:
        """Search for names of PVs matching the given strings.

        Args:
            pvstrings (str | list[str]): A string or list of strings containing
                possible glob search characters.
            start (datetime.datetime | None): Start time of the time period.
            end (datetime.datetime | None): End time of the time period.
            limit (int): Limit of PV names to return for each search string given.
                To get all the PV names, (potentially in the millions), set limit to -1.
                [default: 500]

        Returns:
            list[str]: Sorted and unique list of PV names found.
        """
        pvstrings_list = pvstrings if isinstance(pvstrings, list) else [pvstrings]
        if not pvstrings_list or pvstrings_list == [""]:
            return []

        # Limit returned list of PV to those in time range, if supplied.
        return self._check_for_pvs_in_time_range(
            # Combine the lists of lists that have been returned, remove repeats.
            pv_list_glob_search=set(
                itertools.chain.from_iterable([
                    self._get_matching_pvs(pvstring, limit)
                    for pvstring in pvstrings_list
                ])
            ),
            start=start,
            end=end,
        )

    def _check_for_pvs_in_time_range(
        self,
        pv_list_glob_search: set[str],
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
    ) -> list[str]:
        """Check if data recorded during the given time range for each PV in set.

        If both start and end given, return only PVs which recorded data during that
        time range.

        If start given and end not, return PVs which recorded data between start and
        now.

        If end given and start not, return PVs which recorded any data before end.

        Args:
            pv_list_glob_search (set[str]): Set of pvs data wanted for.
            start (datetime.datetime | None): Start of the time range.
            end (datetime.datetime | None): End of the time range.

        Returns:
            list[str]: Sorted and unique list of PV names found.
        """
        if not start and not end:
            # Return sorted list.
            return sorted(pv_list_glob_search)

        # Add timezone if missing, otherwise convert to UTC.
        start = self._set_timezone_utc(input_time=start) if start else None
        end = (
            self._set_timezone_utc(input_time=end)
            if end
            else datetime.datetime.now(tz=UTC)
        )

        # Set both ends of time range in the data query query to end, then Archiver
        # returns the most recent event prior to end, or an empty result.
        all_events = [self.get_events(pv, end, end) for pv in pv_list_glob_search]

        # Create set of those PVs with atleast one event within specified time range.
        pv_set: set[str] = set()
        for events in all_events:
            pv_set.update(
                event.pv
                for event in events
                if (start and event.pd_timestamp.to_pydatetime(warn=False) >= start)
                or not start
            )

        # Return sorted list.
        return sorted(pv_set)

    @staticmethod
    def _set_timezone_utc(
        input_time: datetime.datetime,
    ) -> datetime.datetime:
        """Add UTC timezone if timezone missing, otherwise convert to UTC.

        Args:
            input_time (datetime.datetime): A timestamp object.

        Returns:
            input_time (datetime.datetime): A timestamp object with timezone set to UTC.
        """
        return (
            input_time.replace(tzinfo=UTC)
            if input_time.tzinfo is None
            else input_time.astimezone(UTC)
        )
