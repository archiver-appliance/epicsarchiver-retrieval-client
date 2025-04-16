"""Archiver Mgmt information module."""

from __future__ import annotations

import logging
from collections.abc import Collection
from enum import Enum
from typing import cast

from epicsarchiver.common.base_archiver import BaseArchiverAppliance

LOG: logging.Logger = logging.getLogger(__name__)

TypeInfo = dict[str, Collection[str]]
InfoResult = dict[str, str]
InfoResultList = list[InfoResult]


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

    # EPICS Archiver Appliance documentation of mgmt endpoints:
    # https://epicsarchiver.readthedocs.io/en/latest/developer/mgmt_scriptables.html

    def get_all_expanded_pvs(self) -> list[str]:
        """Return all expanded PV names in the cluster.

        This is targeted at automation and should return the PVs
        being archived, the fields, .VAL's, aliases and PV's in
        the archive workflow.
        Note this call can return 10's of millions of names.

        Returns:
            list of expanded PV names
        """
        r = self._get("/getAllExpandedPVNames")
        return cast("list[str]", r.json())

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
        params: dict[str, str] = {"limit": str(limit)}
        if pv_query is not None:
            params["pv"] = pv_query
        if regex is not None:
            params["regex"] = regex
        r = self._get("/getAllPVs", params=params)
        return cast("list[str]", r.json())

    def get_pv_status(self, pv: str | list[str]) -> InfoResultList:
        """Return the status of a PV.

        Args:
            pv: name(s) of the pv for which the status is to be
                determined. Can be a GLOB wildcards or multiple PVs as a
                comma separated list.

        Returns:
            list of dict with the status of the matching PVs
        """
        r = self._get("/getPVStatus", params={"pv": pv})
        return cast("InfoResultList", r.json())

    def get_archiving_status(self, pv: str) -> ArchivingStatus | None:
        """Return the status of a PV.

        Args:
            pv: name of the pv.

        Returns:
            string representing the status
        """
        return ArchivingStatus.from_str(self.get_pv_status(pv)[0]["status"])

    def get_pv_details(self, pv: str | list[str]) -> InfoResultList:
        """Return the details of a PV.

        Args:
            pv: name(s) of the pv for which the details are to be
                determined. Can be a GLOB wildcards or multiple PVs as a
                comma separated list.

        Returns:
            list of dict with the details of the matching PVs
        """
        r = self._get("/getPVDetails", params={"pv": pv})
        return cast("InfoResultList", r.json())

    def get_unarchived_pvs(self, pvs: str | list[str]) -> list[str]:
        """Return the list of unarchived PVs out of PVs specified in pvs.

        Args:
            pvs: a list of PVs either in CSV format or as a python
                string list

        Returns:
            list of unarchived PV names
        """
        if isinstance(pvs, list):
            pvs = ",".join(pvs)
        r = self._post("/unarchivedPVs", data={"pv": pvs})
        return cast("list[str]", r.json())

    def get_archived_pvs(self, pvs: str | list[str]) -> list[str]:
        """Return the list of unarchived PVs out of PVs specified in pvs.

        Args:
            pvs: a list of PVs either in CSV format or as a python
                string list

        Returns:
            list of unarchived PV names
        """
        if isinstance(pvs, list):
            pvs = ",".join(pvs)
        r = self._post("/archivedPVs", data={"pv": pvs})
        return cast("list[str]", r.json())

    def get_pv_type_info(self, pv: str) -> TypeInfo:
        """Return the type info of a PV.

        Args:
            pv: name of the pv.

        Returns:
            dict with the type info of the matching PVs.
        """
        r = self._get("/getPVTypeInfo", params={"pv": pv})
        return cast("TypeInfo", r.json())
