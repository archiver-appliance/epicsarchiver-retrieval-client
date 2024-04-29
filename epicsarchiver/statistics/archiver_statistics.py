"""Archiver Statistics module."""

from __future__ import annotations

from epicsarchiver.common.base_archiver import mgmt_url
from epicsarchiver.mgmt.archiver_mgmt import ArchiverMgmt
from epicsarchiver.statistics.async_service import ServiceClient
from epicsarchiver.statistics.stat_responses import (
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    LostConnectionsResponse,
    PausedPVResponse,
    SilentPVsResponse,
    StorageRatesResponse,
)


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
        """Gets the pvs ordered by dropped events."""
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = await self._get_json(reason.value, params=params)
        return [DroppedPVResponse.from_json(rs, reason) for rs in r]

    async def get_disconnected_pvs(self) -> list[DisconnectedPVsResponse]:
        """Gets the list of disconnected pvs."""
        r = await self._get_json("/getCurrentlyDisconnectedPVs")
        return [DisconnectedPVsResponse.from_json(rs) for rs in r]

    async def get_silent_pvs(self, limit: int | None = 1000) -> list[SilentPVsResponse]:
        """Gets the list of pvs with no events."""
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = await self._get_json("/getSilentPVsReport", params=params)
        return [SilentPVsResponse.from_json(rs) for rs in r]

    async def get_lost_connections_pvs(
        self,
        limit: int | None = 1000,
    ) -> list[LostConnectionsResponse]:
        """Gets the list of pvs with no events."""
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = await self._get_json("/getLostConnectionsReport", params=params)
        return [LostConnectionsResponse.from_json(rs) for rs in r]

    async def get_storage_rates(
        self, limit: int | None = 1000
    ) -> list[StorageRatesResponse]:
        """Gets the list of pvs with no events."""
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = await self._get_json("/getStorageRateReport", params=params)
        return [StorageRatesResponse.from_json(rs) for rs in r]

    async def get_paused_pvs(self) -> list[PausedPVResponse]:
        """Gets the list of paused pvs."""
        r = await self._get_json("/getPausedPVsReport")
        return [PausedPVResponse.from_json(rs) for rs in r]


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
