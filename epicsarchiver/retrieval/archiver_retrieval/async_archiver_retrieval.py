"""Module for an asynchronous version of archiver retriever."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pytz import UTC

from epicsarchiver.common.async_service import ServiceClient
from epicsarchiver.retrieval.pb import parse_pb_data

if TYPE_CHECKING:
    import datetime

    from aiohttp import ClientResponse

    from epicsarchiver.retrieval.archive_event import ArchiveEvent
    from epicsarchiver.retrieval.archiver_retrieval.processor import Processor


def _format_date(at: datetime.datetime) -> str:
    return (
        at.astimezone(UTC).replace(tzinfo=None).isoformat(timespec="microseconds") + "Z"
    )


class AsyncArchiverRetrieval(ServiceClient):
    """Async Retrieval EPICS Archiver Appliance client.

    Hold a session to the Retrieval Archiver Appliance web application.

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
        """Create Async Retrieval object.

        Args:
            hostname (str, optional): hostname of archiver.
            port (int, optional): port of archiver mgmt.
        """
        self.hostname = hostname
        self.port = port
        self._data_url: str | None = None
        super().__init__(f"https://{hostname}")

    async def data_url(self) -> str:
        """EPICS Archiver Appliance data retrieval url.

        Raises:
            ConnectionError: Raises if archiver not available

        Returns:
            str: url of retrieval engine
        """
        if self._data_url is None:
            app_info = await self._get_json(
                f"http://{self.hostname}:{self.port}/mgmt/bpl/getApplianceInfo"
            )
            data_url_base = app_info.get("dataRetrievalURL")
            if data_url_base is None:
                raise ConnectionError
            self._data_url = data_url_base + "/data/getData.raw"
        return self._data_url

    async def _get_data_raw(
        self,
        pv: str,
        start: datetime.datetime,
        end: datetime.datetime,
    ) -> ClientResponse:
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
            "from": _format_date(start),
            "to": _format_date(end),
        }
        return await self._get(
            await self.data_url(),
            params=params,
        )

    async def get_events(
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
        """Retrieve archived data.

        Args:
            pvs: list of pvs
            start: start time. Can be a string or `datetime.datetime`
                object.
            end: end time. Can be a string or `datetime.datetime`
                object.
            processor (Processor | None, optional): Preprocessor
                to use. Defaults to None.


        Returns:
            dict[str, list[ArchiveEvent]]: requested events from the archiver.
        """

        async def get_pv_and_events(pv: str) -> tuple[str, list[ArchiveEvent]]:
            return (pv, await self.get_events(pv, start, end, processor=processor))

        requests = [get_pv_and_events(pv) for pv in pvs]
        responses = await asyncio.gather(*requests)
        return dict(responses)
