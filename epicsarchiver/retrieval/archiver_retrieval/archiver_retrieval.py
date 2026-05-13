"""Archiver Retrieval methods."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, cast

from pytz import UTC

from epicsarchiver.common.base_archiver import (
    DEFAULT_RETRIEVAL_PORT,
    BaseArchiverAppliance,
)
from epicsarchiver.common.date_util import (
    QueryTimestamp,
    ensure_utc,
)
from epicsarchiver.common.validation import (
    validate_processor,
    validate_pv,
    validate_start_end,
)
from epicsarchiver.retrieval.pb import parse_pb_data

if TYPE_CHECKING:
    import polars as pl
    from requests import Response

    from epicsarchiver.retrieval.archive_event import ArchiveEventsData
    from epicsarchiver.retrieval.archiver_retrieval.processor import Processor


LOG: logging.Logger = logging.getLogger(__name__)

ENDPOINT_GET_DATA = "/data/getData.raw"
ENDPOINT_GET_MATCHING_PVS = "/bpl/getMatchingPVs"


class ArchiverRetrieval(BaseArchiverAppliance):
    """Retrieval EPICS Archiver Appliance client.

    Hold a session to the Retrieval Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname
        port: EPICS Archiver Appliance retrieval port

    Examples:

    .. code-block:: python

        from epicsarchiver.archiver.retrieval import ArchiverRetrieval

        archappl = ArchiverRetrieval("archiver-01.tn.esss.lu.se")
        print(archappl.version)
        df = archappl.get_data("my:pv", start="2018-07-04 13:00", end=datetime.utcnow())
    """

    def __init__(self, hostname: str = "localhost", port: int = DEFAULT_RETRIEVAL_PORT):
        """Create Archiver Appliance object.

        Args:
            hostname (str, optional): hostname of archiver.
            port (int, optional): port number of retrieval interface.
        """
        super().__init__(hostname, port)
        self._base_url = f"http://{self.hostname}:{self.port}/retrieval"
        self.data_url: str = self._base_url + ENDPOINT_GET_DATA
        self.matching_pvs_url: str = self._base_url + ENDPOINT_GET_MATCHING_PVS

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
            "from": QueryTimestamp.from_datetime(start).to_query_string(),
            "to": QueryTimestamp.from_datetime(end).to_query_string(),
        }
        return self._get(
            self.data_url,
            params=params,
        )

    def _get_matching_pvs(
        self,
        query: str,
        limit: int,
    ) -> list[str]:
        """Retrieve list of matching pv names for given regex search string.

        Args:
            query (str): A regex search string.
            limit (int): Limit of PV names to return.

        Returns:
            list[str]: List of pv names
        """
        params = {
            "regex": query,
            "limit": str(limit),
        }
        return cast(
            "list[str]",
            self._get(
                self.matching_pvs_url,
                params=params,
            ).json(),
        )

    def _check_for_pvs_in_time_range(
        self,
        query: list[str],
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
    ) -> list[str]:
        """Check if data recorded during the given time range for each PV in list.

        If both start and end given, return only PVs which recorded data during that
        time range.

        If start given and end not, return PVs which recorded data between start and
        now.

        If end given and start not, return PVs which recorded any data before end.

        Args:
            query (list[str]): List of pvs.
            start (datetime.datetime | None): Start of the time range.
            end (datetime.datetime | None): End of the time range.

        Returns:
            list[str]: List of PV names found.
        """
        if not start and not end:
            return query

        # Add timezone if missing, otherwise convert to UTC.
        start = ensure_utc(start) if start else None
        end = ensure_utc(end) if end else datetime.datetime.now(tz=UTC)

        # Set both ends of time range in the data query query to end, then Archiver
        # returns the most recent event prior to end, or an empty result.
        all_events = [self.get_events(pv, end, end)[1] for pv in query]

        # Create list of those PVs with atleast one event within specified time range.
        pv_list: list[str] = []
        for events in all_events:
            pv_list.extend(
                event.pv
                for event in events
                if (start and event.timestamp >= start) or not start
            )

        return pv_list

    def get_events(
        self,
        pv: str,
        start: datetime.datetime,
        end: datetime.datetime,
        processor: Processor | None = None,
    ) -> ArchiveEventsData:
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
            ArchiveEventsData: tuple of (metadata, events).
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        validate_pv(pv)
        validate_start_end(start, end)
        validate_processor(processor)
        pv_request = processor.calc_pv_name(pv) if processor else pv
        r = self._get_data_raw(pv_request, start, end)
        pb_data = r.content
        data = parse_pb_data(pb_data)
        LOG.debug("Metadata: %s", data[0])
        return data

    def get_data(
        self,
        pv: str,
        start: str | datetime.datetime,
        end: str | datetime.datetime,
        processor: Processor | None = None,
    ) -> pl.DataFrame:
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
            `polars.DataFrame`

        Raises:
            ImportError: If the polars extra is not installed.
        """
        try:
            from epicsarchiver.retrieval.dataframe import (  # noqa: PLC0415
                dataframe_from_events,
            )
        except ImportError as exc:
            msg = "polars extra required: pip install epicsarchiver-retrieval-client[polars]"
            raise ImportError(msg) from exc
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        start_time = QueryTimestamp.from_input(start).datetime
        end_time = QueryTimestamp.from_input(end).datetime
        metadata, events = self.get_events(pv, start_time, end_time, processor)
        return dataframe_from_events(events, metadata)

    def search(
        self,
        query: str,
        *,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        limit: int = 500,
    ) -> list[str]:
        """Search for names of PVs matching the given regex search string.

        Optionally specify start and/or end times to only return PVs that recorded data
        in the specified time range.

        Args:
            query (str): A regex search string.
            start (datetime.datetime | None): Start time of the time period.
            end (datetime.datetime | None): End time of the time period.
            limit (int): Limit of PV names to return for each search string given.
                To get all the PV names, (potentially in the millions), set limit to -1.
                [default: 500]

        Returns:
            list[str]: List of PV names found.
        """
        # Limit returned list of PV to those in time range, if supplied.
        return self._check_for_pvs_in_time_range(
            query=self._get_matching_pvs(query, limit),
            start=start,
            end=end,
        )
