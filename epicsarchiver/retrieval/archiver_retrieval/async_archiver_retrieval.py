"""Module for an asynchronous version of archiver retriever."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, cast

from pytz import UTC
from typing_extensions import Self

from epicsarchiver.common.async_service import ServiceClient
from epicsarchiver.common.date_util import format_date, set_timezone_utc
from epicsarchiver.common.validation import (
    validate_processor,
    validate_pv,
    validate_start_end,
)
from epicsarchiver.retrieval.pb import ArchiveEventsData, parse_pb_data

if TYPE_CHECKING:
    from aiohttp import ClientResponse

    from epicsarchiver.retrieval.archive_event import ArchiveEvent
    from epicsarchiver.retrieval.archiver_retrieval.processor import Processor

LOG: logging.Logger = logging.getLogger(__name__)

ENDPOINT_GET_DATA = "/data/getData.raw"
ENDPOINT_GET_MATCHING_PVS = "/bpl/getMatchingPVs"


class AsyncArchiverRetrieval(ServiceClient):
    """Async retrieval client for the EPICS archiver appliance.

    Hold a session to the Archiver Appliance server to make retrieval requests.

    Args:
        hostname: EPICS Archiver Appliance hostname [default: localhost]
        port: EPICS Archiver Appliance management port [default: 17665]

    Examples:

    .. code-block:: python

        from epicsarchiver.archiver.retrieval import AsyncArchiverRetrieval

        async with AsyncArchiverRetrieval("archiver-01.tn.esss.lu.se") as archappl:
            events = await archappl.get_events(
                "my:pv",
                start=datetime.now(tz=UTC) - timedelta(seconds=1),
                end=datetime.utcnow(),
            )
    """

    def __init__(self, hostname: str = "localhost", port: int = 17665):
        """Create Async archiver retrieval client.

        Args:
            hostname (str, optional): hostname of archiver.
            port (int, optional): port of archiver mgmt.
        """
        self.hostname = hostname
        self.port = port

        super().__init__(f"https://{hostname}")

        self._data_retrieval_url: str = ""
        self.data_url: str = ""
        self.matching_pvs_url: str = ""

    async def __aenter__(self) -> Self:
        """Asynchronous enter.

        Set url endpoints that will be used in this class:
            self.data_url: EPICS Archiver Appliance data retrieval URL.
                Use this url to retrieve pv data.
            self.matching_pvs_url: EPICS Archiver Appliance matching PVs URL.
                Use this url to search for pv names matching an input search string that
                can contain regex patterns.

        Returns:
            Self: self
        """
        app_info = await self._get_json(
            f"http://{self.hostname}:{self.port}/mgmt/bpl/getApplianceInfo"
        )
        self._data_retrieval_url = app_info["dataRetrievalURL"]
        self.data_url = self._data_retrieval_url + ENDPOINT_GET_DATA
        self.matching_pvs_url = self._data_retrieval_url + ENDPOINT_GET_MATCHING_PVS
        return self

    async def _get_data_raw(
        self,
        pv: str,
        start: datetime.datetime,
        end: datetime.datetime,
    ) -> ClientResponse:
        """Fetch raw response from archiver data retrieval URL.

        Args:
            pv (str): PV data requested for.
            start (datetime.datetime): Start time of period.
            end (datetime.datetime): End time of period.

        Returns:
            ClientResponse: Raw response from the archiver.
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        params = {
            "pv": pv,
            "from": format_date(start),
            "to": format_date(end),
            "fetchLatestMetadata": "true",
        }
        return await self._get(self.data_url, params=params)

    async def _get_matching_pvs(
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
        return_value = await self._get_json(self.matching_pvs_url, params=params)
        return cast("list[str]", return_value)

    async def _check_for_pvs_in_time_range(
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
        start = set_timezone_utc(input_time=start) if start else None
        end = set_timezone_utc(input_time=end) if end else datetime.datetime.now(tz=UTC)

        # Set both ends of time range in the data query query to end, then Archiver
        # returns the most recent event prior to end, or an empty result.
        all_events = await self.get_all_events(set(query), end, end)

        # Create list of those PVs with atleast one event within specified time range.
        pv_list: list[str] = []
        for events in all_events.values():
            pv_list.extend(
                event.pv
                for event in events
                if (start and event.timestamp >= start) or not start
            )

        return pv_list

    async def get_events(
        self,
        pv: str,
        start: datetime.datetime,
        end: datetime.datetime,
        processor: Processor | None = None,
    ) -> list[ArchiveEvent]:
        """Get a list of events from the archiver for specified pv and time period.

        Args:
            pv (str): PV data requested for.
            start (datetime.datetime): Start time of the time period.
            end (datetime.datetime): End time of the time period.
            processor (Processor | None, optional): Optional Preprocessor to use.
                Defaults to None.

        Returns:
            list[ArchiveEvent]: List of events in time period.
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        metadata, events = await self.get_archive_data(pv, start, end, processor)
        LOG.debug("Metadata: %s", metadata)
        return events

    async def get_archive_data(
        self,
        pv: str,
        start: datetime.datetime,
        end: datetime.datetime,
        processor: Processor | None = None,
    ) -> ArchiveEventsData:
        """Get events from the archiver for specified pv and time period with metadata.

        Args:
            pv (str): PV data requested for.
            start (datetime.datetime): Start time of the time period.
            end (datetime.datetime): End time of the time period.
            processor (Processor | None, optional): Optional Preprocessor to use.
                Defaults to None.

        Returns:
            ArchiveEventsData: Metadata per year, list of events in time period.
        """
        validate_pv(pv)
        validate_start_end(start, end)
        validate_processor(processor)
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        pv_request = processor.calc_pv_name(pv) if processor else pv
        r = await self._get_data_raw(pv_request, start, end)
        pb_data = await r.content.read()
        return parse_pb_data(pb_data)

    async def get_all_events(
        self,
        pvs: set[str],
        start: datetime.datetime,
        end: datetime.datetime,
        processor: Processor | None = None,
    ) -> dict[str, list[ArchiveEvent]]:
        """Get a list of events for every pv requested.

        Makes all the calls to the archiver asynchronously, so some maybe made in
        parallel.

        Args:
            pvs (set[str]): Set of pvs data wanted for.
            start (datetime.datetime): Start time of period.
            end (datetime.datetime): End time of period.
            processor (Processor | None, optional): Optional choice of Preprocessor.
                Defaults to None.

        Returns:
            dict[str, list[ArchiveEvent]]: Dictionary of pvs (keys) and events (values).
        """

        async def get_pv_and_events(pv: str) -> tuple[str, list[ArchiveEvent]]:
            return (pv, await self.get_events(pv, start, end, processor=processor))

        requests = [get_pv_and_events(pv) for pv in pvs]
        responses = await asyncio.gather(*requests)
        return dict(responses)

    async def search(
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
        return await self._check_for_pvs_in_time_range(
            await self._get_matching_pvs(query, limit),
            start=start,
            end=end,
        )
