"""ArchiverMgmt module."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, cast

from epicsarchiver.common.base_archiver import BaseArchiverAppliance
from epicsarchiver.mgmt import archive_files

LOG: logging.Logger = logging.getLogger(__name__)


class ArchiverMgmt(BaseArchiverAppliance):
    """Mgmt EPICS Archiver Appliance client.

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

    def archive_pv(self, pv: str, **kwargs: Any) -> list[dict[str, str]]:
        r"""Archive a PV.

        Args:
            pv: name of the pv to be achived. Can be a comma separated
                list of names.
            **kwargs: optional extra keyword arguments -
                samplingperiod - samplingmethod - controllingPV - policy
                - appliance

        Returns:
            list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ArchivePVAction.html
        params = {"pv": pv}
        params.update(kwargs)
        r = self._get("/archivePV", params=params)
        return cast(List[Dict[str, str]], r.json())

    def archive_pvs(self, pvs: list[dict[str, str]]) -> list[dict[str, str]]:
        """Archive a list of PVs.

        Args:
            pvs: list of PVs (as dict) to archive

        Returns:
            list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ArchivePVAction.html
        r = self._post("/archivePV", json=pvs)
        return cast(List[Dict[str, str]], r.json())

    def archive_pvs_from_files(
        self,
        files: list[str],
        appliance: str | None = None,
    ) -> list[dict[str, str]]:
        """Archive PVs from a list of files.

        Args:
            files: list of files in CSV format with PVs to archive.
            appliance: optional appliance to use to archive PVs (in a
                cluster)

        Returns:
            list of submitted PVs
        """
        pvs = archive_files.get_pvs_from_files([Path(f) for f in files], appliance)
        return self.archive_pvs(pvs)

    def pause_pv(self, pv: str) -> list[dict[str, str]] | dict[str, str]:
        """Pause the archiving of a PV(s).

        Args:
            pv: name of the pv. Can be a GLOB wildcards or a list of
                comma separated names.

        Returns:
            list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/PauseArchivingPV.html
        response = self._get_or_post("/pauseArchivingPV", pv)
        if "," not in pv:
            return cast(Dict[str, str], response)
        return cast(List[Dict[str, str]], response)

    def resume_pv(self, pv: str) -> list[dict[str, str]] | dict[str, str]:
        """Resume the archiving of a PV(s).

        Args:
            pv: name of the pv. Can be a GLOB wildcards or a list of
                comma separated names.

        Returns:
            list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ResumeArchivingPV.html
        response = self._get_or_post("/resumeArchivingPV", pv)
        if "," not in pv:
            return cast(Dict[str, str], response)
        return cast(List[Dict[str, str]], response)

    def abort_pv(self, pv: str) -> list[str]:
        """Abort any pending requests for archiving this PV.

        Args:
            pv: name of the pv.

        Returns:
            list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/AbortArchiveRequest.html
        r = self._get("/abortArchivingPV", params={"pv": pv})
        return cast(List[str], r.json())

    def delete_pv(
        self,
        pv: str,
        delete_data: bool = False,  # noqa: FBT002, FBT001
    ) -> list[str]:
        """Stop archiving the specified PV.

        The PV needs to be paused first.

        Args:
            pv: name of the pv.
            delete_data: delete the data that has already been recorded.
                Default to False.

        Returns:
            list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/DeletePV.html
        r = self._get("/deletePV", params={"pv": pv, "delete_data": delete_data})
        return cast(List[str], r.json())

    def rename_pv(self, pv: str, newname: str) -> dict[str, str]:
        """Rename this pv to a new name.

        The PV needs to be paused first.

        Args:
            pv (str): name of the pv.
            newname (str): new name of the pv

        Returns:
            dict[str, str]: Status of action and description. Example:
                {"status":"ok","desc":"Successfully renamed PV PV1 to PV2"}
        """
        # https://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/RenamePVAction.html
        r = self._get("/renamePV", params={"pv": pv, "newname": newname})
        return cast(Dict[str, str], r.json())

    def update_pv(
        self,
        pv: str,
        samplingperiod: float,
        samplingmethod: str | None = None,
    ) -> list[str]:
        """Change the archival parameters for a PV.

        Args:
            pv: name of the pv.
            samplingperiod: the new sampling period in seconds.
            samplingmethod: the new sampling method [SCAN|MONITOR]

        Returns:
            list of submitted PV
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ChangeArchivalParamsAction.html
        params = {"pv": pv, "samplingperiod": samplingperiod}
        if samplingmethod:
            params["samplingmethod"] = samplingmethod
        r = self._get("/changeArchivalParameters", params=params)
        return cast(List[str], r.json())

    def pause_rename_resume_pv(self, pv: str, new: str) -> None:
        """Pause, rename and resume a PV.

        Args:
            pv: name of the pv
            new: new name of the pv

        Returns:
            None
        """
        result = self.get_pv_status(pv)
        if result[0]["status"] != "Being archived":
            LOG.error("PV %s isn't being archived. Skipping.\n", pv)
            return
        result = self.get_pv_status(new)
        if result[0]["status"] != "Not being archived":
            LOG.error("New PV %s already exists. Skipping.\n", new)
            return
        cresult = self.pause_pv(pv)
        if not check_result(cresult, f"Error while pausing {pv}"):
            return
        cresult = self.rename_pv(pv, new)
        if not check_result(cresult, f"Error while renaming {pv} to {new}"):
            return
        cresult = self.resume_pv(new)
        if not check_result(cresult, f"Error while resuming {new}"):
            return
        LOG.debug("PV %s successfully renamed to %s", pv, new)

    def rename_pvs_from_files(self, files: list[str]) -> None:
        """Rename PVs from a list of files.

        Each PV will be paused, renamed and resumed

        Args:
            files: list of files in CSV format with PVs to rename.

        Returns:
            None
        """
        pvs = archive_files.get_rename_pvs_from_files(files)
        for current, new in pvs:
            self.pause_rename_resume_pv(current, new)


def check_result(
    result: dict[str, str] | list[dict[str, str]],
    default_message: str | None = None,
) -> bool:
    """Check a result returned by the Archiver Appliance.

    Return True if the status is ok
    Return False otherwise and print the default_message or validation value
    """
    if isinstance(result, list):
        LOG.error(
            "Method check_result does not support multiple PVs from result %s",
            result,
        )
        return False
    status = result.get("status", "nok")
    if status.lower() != "ok":
        message = result.get("validation", default_message)
        LOG.error(message)
        return False
    return True
