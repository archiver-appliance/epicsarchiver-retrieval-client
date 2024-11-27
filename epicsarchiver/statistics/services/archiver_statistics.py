"""Archiver Statistics Service."""

from __future__ import annotations

import asyncio

from epicsarchiver.common.base_archiver import mgmt_url
from epicsarchiver.mgmt.archiver_mgmt import ArchiverMgmt
from epicsarchiver.statistics.models.pv_details import DetailEnum, Details
from epicsarchiver.statistics.models.stat_responses import (
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    LostConnectionsResponse,
    PausedPVResponse,
    SilentPVsResponse,
    StorageRatesResponse,
)
from epicsarchiver.statistics.models.stats import PVStats
from epicsarchiver.statistics.services.async_service import ServiceClient


class ArchiverStatistics(ServiceClient):
    """Responses from the reports of the archiver appliance."""

    def __init__(self, hostname: str = "localhost", port: int = 17665):
        """Create Archiver Appliance object.

        Args:
            hostname (str, optional): hostname of archiver. Defaults to "localhost".
            port (int, optional): port number of mgmt interface. Defaults to 17665.
        """
        self.hostname = hostname
        super().__init__(mgmt_url(hostname, port))

    async def get_pvs_dropped(
        self,
        reason: DroppedReason,
        limit: int | None = 1000,
    ) -> list[DroppedPVResponse]:
        """Gets the pvs ordered by dropped events.

        Returns:
            list[DroppedPVResponse]: List of responses
        """
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = await self._get_json(reason.value, params=params)
        return [DroppedPVResponse.from_json(rs, reason) for rs in r]

    async def get_disconnected_pvs(self) -> list[DisconnectedPVsResponse]:
        """Gets the list of disconnected pvs.

        Returns:
            list[DisconnectedPVsResponse]: List of responses
        """
        r = await self._get_json("/getCurrentlyDisconnectedPVs")
        return [DisconnectedPVsResponse.from_json(rs) for rs in r]

    async def get_silent_pvs(self, limit: int | None = 1000) -> list[SilentPVsResponse]:
        """Gets the list of pvs with no events.

        Returns:
            list[SilentPVsResponse]: List of responses
        """
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = await self._get_json("/getSilentPVsReport", params=params)
        return [SilentPVsResponse.from_json(rs) for rs in r]

    async def get_lost_connections_pvs(
        self,
        limit: int | None = 1000,
    ) -> list[LostConnectionsResponse]:
        """Gets the list of pvs with no events.

        Returns:
            list[LostConnectionsResponse]: List of responses
        """
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = await self._get_json("/getLostConnectionsReport", params=params)
        return [LostConnectionsResponse.from_json(rs) for rs in r]

    async def get_storage_rates(
        self, limit: int | None = 1000
    ) -> list[StorageRatesResponse]:
        """Gets the list of pvs with no events.

        Returns:
            list[StorageRatesResponse]: List of responses
        """
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = await self._get_json("/getStorageRateReport", params=params)
        return [StorageRatesResponse.from_json(rs) for rs in r]

    async def get_paused_pvs(self) -> list[PausedPVResponse]:
        """Gets the list of paused pvs.

        Returns:
            list[PausedPVResponse]: List of responses
        """
        r = await self._get_json("/getPausedPVsReport")
        return [PausedPVResponse.from_json(rs) for rs in r]

    async def get_pv_details(
        self, pvs: list[str], mb_per_day_min: float = 0
    ) -> dict[str, PVStats]:
        """Return the details of a PV.

        Args:
            pvs (list[str]): names of the pvs for which the details are to be
                determined.
            mb_per_day_min (float): Minimum MB per day to filter by

        Returns:
            list of dict with the details of the matching PVs
        """
        base_details = await asyncio.gather(*[
            self._get_json("/getPVDetails", params={"pv": pv}) for pv in pvs
        ])
        details = [Details.from_json(dets) for dets in base_details]
        # Convert each detail to stat_responses
        return {
            pv_details[DetailEnum.PVName]: PVStats(
                pv_details[DetailEnum.PVName],
                pv_details.to_base_responses(mb_per_day_min),
            )
            for pv_details in details
        }


class ArchiverWrapper:
    """Wrapper around ArchiverStatistics and ArchiverMgmt for Statistics usage."""

    def __init__(self, hostname: str = "localhost", port: int = 17665):
        """Create Archiver Appliance object.

        Args:
            hostname (str, optional): hostname of archiver. Defaults to "localhost".
            port (int, optional): port number of mgmt interface. Defaults to 17665.
        """
        self.mgmt = ArchiverMgmt(hostname, port)
        self.stats = ArchiverStatistics(hostname)

    async def close(self) -> None:
        """Closes any connected sessions."""
        if self.stats:
            await self.stats.close()

    def __repr__(self) -> str:
        """String representation of ArchiverWrapper.

        Returns:
            str: ouput string
        """
        return f"ArchiverWrapper({self.mgmt.hostname}, {self.mgmt.port})"
