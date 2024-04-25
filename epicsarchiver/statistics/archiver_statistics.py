"""Archiver Statistics module."""

from epicsarchiver.common.base_archiver import BaseArchiverAppliance
from epicsarchiver.statistics.stat_responses import (
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    LostConnectionsResponse,
    PausedPVResponse,
    SilentPVsResponse,
    StorageRatesResponse,
)


class ArchiverStatistics(BaseArchiverAppliance):
    """Responses from the reports of the archiver appliance."""

    def get_pvs_dropped(
        self,
        reason: DroppedReason,
        limit: int | None = 1000,
    ) -> list[DroppedPVResponse]:
        """Gets the pvs ordered by dropped events."""
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = self._get(reason.value, params=params).json()
        return [DroppedPVResponse.from_json(rs, reason) for rs in r]

    def get_disconnected_pvs(self) -> list[DisconnectedPVsResponse]:
        """Gets the list of disconnected pvs."""
        r = self._get("/getCurrentlyDisconnectedPVs").json()
        return [DisconnectedPVsResponse.from_json(rs) for rs in r]

    def get_silent_pvs(self, limit: int | None = 1000) -> list[SilentPVsResponse]:
        """Gets the list of pvs with no events."""
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = self._get("/getSilentPVsReport", params=params).json()
        return [SilentPVsResponse.from_json(rs) for rs in r]

    def get_lost_connections_pvs(
        self,
        limit: int | None = 1000,
    ) -> list[LostConnectionsResponse]:
        """Gets the list of pvs with no events."""
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = self._get("/getLostConnectionsReport", params=params).json()
        return [LostConnectionsResponse.from_json(rs) for rs in r]

    def get_storage_rates(self, limit: int | None = 1000) -> list[StorageRatesResponse]:
        """Gets the list of pvs with no events."""
        params = None
        if limit:
            params = {"limit": str(limit)}
        r = self._get("/getStorageRateReport", params=params).json()
        return [StorageRatesResponse.from_json(rs) for rs in r]

    def get_paused_pvs(self) -> list[PausedPVResponse]:
        """Gets the list of paused pvs."""
        r = self._get("/getPausedPVsReport").json()
        return [PausedPVResponse.from_json(rs) for rs in r]
