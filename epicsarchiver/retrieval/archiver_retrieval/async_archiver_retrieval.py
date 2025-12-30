"""Module for an asynchronous version of archiver retriever."""

from __future__ import annotations

import asyncio
import fnmatch
import itertools
import logging
from typing import TYPE_CHECKING, Any

from epicsarchiver.common.async_service import ServiceClient
from epicsarchiver.common.date_util import format_date
from epicsarchiver.common.errors import ArchiverResponseError
from epicsarchiver.common.validation import (
    validate_processor,
    validate_pv,
    validate_start_end,
)
from epicsarchiver.retrieval.pb import ArchiveEventsData, parse_pb_data

if TYPE_CHECKING:
    import datetime

    from aiohttp import ClientResponse

    from epicsarchiver.retrieval.archive_event import ArchiveEvent
    from epicsarchiver.retrieval.archiver_retrieval.processor import Processor

LOG: logging.Logger = logging.getLogger(__name__)


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
        self._data_url: str | None = None
        self._matching_pvs_url: str | None = None
        super().__init__(f"https://{hostname}")

    async def data_url(self) -> str:
        """EPICS Archiver Appliance data retrieval URL.

        Raises:
            ArchiverResponseError: Raises if archiver not available

        Returns:
            str: URL of retrieval engine
        """
        if self._data_url is None:
            app_info = await self._get_json(
                f"http://{self.hostname}:{self.port}/mgmt/bpl/getApplianceInfo"
            )
            data_url_base = app_info.get("dataRetrievalURL")
            if data_url_base is None:
                msg = "Missing dataRetrievalURL in response from getApplianceInfo."
                raise ArchiverResponseError(msg)
            self._data_url = data_url_base + "/data/getData.raw"
        return self._data_url

    async def matching_pvs_url(self) -> str:
        """EPICS Archiver Appliance matching PVs URL.

        Raises:
            ArchiverResponseError: Raises if archiver not available

        Returns:
            str: URL of retrieval engine
        """
        if self._matching_pvs_url is None:
            app_info = await self._get_json(
                f"http://{self.hostname}:{self.port}/mgmt/bpl/getApplianceInfo"
            )
            retrieval_url_base = app_info.get("retrievalURL")
            if retrieval_url_base is None:
                msg = "Missing retrievalURL in response from getApplianceInfo."
                raise ArchiverResponseError(msg)
            self._matching_pvs_url = retrieval_url_base + "/getMatchingPVs"
        return self._matching_pvs_url

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
        return await self._get(
            await self.data_url(),
            params=params,
        )

    async def _get_matching_pvs(
        self,
        pv: str,
        limit: int,
    ) -> Any:
        """Retrieve list of matching pv names for given glob search string.

        Args:
            pv (str): PV glob name search string.
            limit (int): Limit of PV names to return.

        Returns:
            Any: Json conversion of :class:`ClientResponse` object
        """
        params = {
            # Convert glob patterns to regex, case insensitive
            "regex": "(?i)" + fnmatch.translate(pv),
            "limit": str(limit),
        }
        return await self._get_json(
            await self.matching_pvs_url(),
            params=params,
        )

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

    async def search(
        self,
        pvstrings: str | list[str] | tuple[str],
        limit: int = 500,
    ) -> list[str]:
        """Search for names of PVs matching the given strings.

        Args:
            pvstrings (str | list[str] | tuple[str]): A string, list of strings, or
                tuple of strings containing possible glob search characters.
            limit (int): Limit of PV names to return for each search string given.
                To get all the PV names, (potentially in the millions), set limit to -1.
                [default: 500]

        Returns:
            list[str]: Sorted and unique list of PV names found.
        """
        pvstrings_list = (
            pvstrings if isinstance(pvstrings, (list, tuple)) else [pvstrings]
        )
        if not pvstrings_list or pvstrings_list == [""]:
            return []

        async def get_matching_pvs(pvstring: str, limit: int) -> Any:
            return await self._get_matching_pvs(pvstring, limit)

        requests = [get_matching_pvs(pvstring, limit) for pvstring in pvstrings_list]
        responses = await asyncio.gather(*requests)
        # Combine the lists of lists that have been returned, remove repeated names,
        # sort.
        return sorted(set(itertools.chain.from_iterable(responses)))

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
