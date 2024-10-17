"""Archiver Mgmt information module."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, cast

from epicsarchiver.common.base_archiver import BaseArchiverAppliance
from epicsarchiver.mgmt import archive_files

LOG: logging.Logger = logging.getLogger(__name__)


class ArchivingStatus(str, Enum):
    """Enum of archiving status in the archiver."""

    Paused = "Paused"
    BeingArchived = "Being archived"
    NotBeingArchived = "Not being archived"

    @classmethod
    def from_str(cls, desc: str) -> ArchivingStatus | None:
        """Convert from a string to ArchivingStatus.

        Args:
            desc (str): input string

        Returns:
            ArchivingStatus | None: An enum representation.
        """
        for e in ArchivingStatus:
            if e.value == desc:
                return e
        return None


class ArchiverMgmtInfo(BaseArchiverAppliance):
    """Mgmt Info EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application and use the mgmt interface.

    Args:
        hostname: EPICS Archiver Appliance hostname [default: localhost]
        port: EPICS Archiver Appliance management port [default: 17665]

    Examples:
    .. code-block:: python

        from epicsarchiver.archiver.mgmt import ArchiverMgmt

        archappl = ArchiverMgmt("archiver-01.tn.esss.lu.se")
        print(archappl.version)
        archappl.get_pv_status(pv="BPM*")
    """

    def get_all_expanded_pvs(self) -> list[str]:
        """Return all expanded PV names in the cluster.

        This is targeted at automation and should return the PVs
        being archived, the fields, .VAL's, aliases and PV's in
        the archive workflow.
        Note this call can return 10's of millions of names.

        Returns:
            list of expanded PV names
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetAllExpandedPVNames.html
        r = self._get("/getAllExpandedPVNames")
        return cast(List[str], r.json())

    def get_all_pvs(
        self,
        pv_query: str | None = None,
        regex: str | None = None,
        limit: int = 500,
    ) -> list[str]:
        """Return all the PVs in the cluster.

        Args:
            pv_query (str): An optional argument that can contain a GLOB wildcard.
                Will return PVs that match this GLOB. For example:
                pv=KLYS*
            regex (str): An optional argument that can contain a Java regex \
                wildcard. Will return PVs that match this regex.
            limit (int): number of matched PV's that are returned. To get all
                the PV names, (potentially in the millions), set limit
                to -1. Default to 500.

        Returns:
            list[str]: list of PV names
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetAllPVs.html
        params: dict[str, str] = {"limit": str(limit)}
        if pv_query is not None:
            params["pv"] = pv_query
        if regex is not None:
            params["regex"] = regex
        r = self._get("/getAllPVs", params=params)
        return cast(List[str], r.json())

    def get_pv_status(self, pv: str | list[str]) -> list[dict[str, str]]:
        """Return the status of a PV.

        Args:
            pv: name(s) of the pv for which the status is to be
                determined. Can be a GLOB wildcards or multiple PVs as a
                comma separated list.

        Returns:
            list of dict with the status of the matching PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetPVStatusAction.html
        r = self._get("/getPVStatus", params={"pv": pv})
        return cast(List[Dict[str, str]], r.json())

    def get_archiving_status(self, pv: str) -> ArchivingStatus | None:
        """Return the status of a PV.

        Args:
            pv: name of the pv.

        Returns:
            string representing the status
        """
        return ArchivingStatus.from_str(self.get_pv_status(pv)[0]["status"])

    def get_pv_details(self, pv: str | list[str]) -> list[dict[str, str]]:
        """Return the details of a PV.

        Args:
            pv: name(s) of the pv for which the details are to be
                determined. Can be a GLOB wildcards or multiple PVs as a
                comma separated list.

        Returns:
            list of dict with the details of the matching PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetPVDetailsAction.html
        r = self._get("/getPVDetails", params={"pv": pv})
        return cast(List[Dict[str, str]], r.json())

    def get_pv_status_from_files(
        self,
        files: list[str],
        appliance: str | None = None,
    ) -> list[dict[str, str]]:
        """Return the status of PVs from a list of files.

        Args:
            files: list of files in CSV format with PVs to archive.
            appliance: optional appliance to use to archive PVs (in a
                cluster)

        Returns:
            list of dict with the status of the matching PVs
        """
        pvs = archive_files.get_pvs_from_files([Path(f) for f in files], appliance)
        lpvs = ",".join(pv["pv"] for pv in pvs)
        return self.get_pv_status(lpvs)

    def get_unarchived_pvs(self, pvs: str | list[str]) -> list[str]:
        """Return the list of unarchived PVs out of PVs specified in pvs.

        Args:
            pvs: a list of PVs either in CSV format or as a python
                string list

        Returns:
            list of unarchived PV names
        """
        # https://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/UnarchivedPVsAction.html
        if isinstance(pvs, list):
            pvs = ",".join(pvs)
        r = self._post("/unarchivedPVs", data={"pv": pvs})
        return cast(List[str], r.json())

    def get_archived_pvs(self, pvs: str | list[str]) -> list[str]:
        """Return the list of unarchived PVs out of PVs specified in pvs.

        Args:
            pvs: a list of PVs either in CSV format or as a python
                string list

        Returns:
            list of unarchived PV names
        """
        # https://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ArchivedPVsAction.html
        if isinstance(pvs, list):
            pvs = ",".join(pvs)
        r = self._post("/archivedPVs", data={"pv": pvs})
        return cast(List[str], r.json())

    def get_unarchived_pvs_from_files(
        self,
        files: list[str],
        appliance: str | None = None,
    ) -> list[str]:
        """Return the list of unarchived PVs from a list of files.

        Args:
            files: list of files in CSV format with PVs to archive.
            appliance: optional appliance to use to archive PVs (in a
                cluster)

        Returns:
            list of unarchived PV names
        """
        pvs = archive_files.get_pvs_from_files([Path(f) for f in files], appliance)
        lpvs = ",".join(pv["pv"] for pv in pvs)
        return self.get_unarchived_pvs(lpvs)
