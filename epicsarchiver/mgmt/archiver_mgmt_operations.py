"""Archiver Mgmt operations module."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, cast

from epicsarchiver.mgmt import archive_files
from epicsarchiver.mgmt.archiver_mgmt_info import ArchiverMgmtInfo, ArchivingStatus

LOG: logging.Logger = logging.getLogger(__name__)


class ArchiverMgmtOperations(ArchiverMgmtInfo):
    """Mgmt Operations EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application and use the mgmt interface.

    Args:
        hostname: EPICS Archiver Appliance hostname [default: localhost]
        port: EPICS Archiver Appliance management port [default: 17665]

    Examples:
    .. code-block:: python

        from epicsarchiver.archiver.mgmt import ArchiverMgmtOperations

        archappl = ArchiverMgmtOperations("archiver-01.tn.esss.lu.se")
        print(archappl.version)
        archappl.archive_pv("PVNAME")
    """

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

    def add_alias(self, pv: str, alias_name: str) -> None:
        """Add an alias to a pv.

        Args:
            pv: PV to add alias.
            alias_name: name of alias to add to pv.

        Returns:
            None
        """
        r = self._get("/addAlias", params={"pv": pv, "aliasname": alias_name})
        r_json = r.json()
        if r_json["status"] != "ok":
            LOG.error("Failed to add alias, response %s", str(r_json))
            return
        LOG.debug(r_json["desc"])

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
        result = self.get_archiving_status(pv)
        if result != ArchivingStatus.BeingArchived:
            LOG.error("PV %s isn't being archived. Skipping.\n", pv)
            return
        result = self.get_archiving_status(new)
        if result != ArchivingStatus.NotBeingArchived:
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

    def rename_and_append(self, old: str, new: str, storage: str) -> None:
        """Appends the data for an older PV into a newer PV.

        The older PV is deleted and an alias mapping the older PV name to
        the new PV is added.

        Args:
            old (str): The name of the older pv.
                The data for this PV will be appended to the newer PV and then deleted.
            new (str): The name of the newer pv.
            storage (str):  The name of the store to consolidate data before appending.
                This is typically a string like LTS.

        Returns:
            None
        """
        pvs = [old, new]
        for pv in pvs:
            status = self.get_archiving_status(pv)
            if status != ArchivingStatus.Paused:
                LOG.error("PV %s isn't paused. Skipping.\n", pv)
                return
        response = self._get(
            "/appendAndAliasPV",
            params={"olderpv": old, "newerpv": new, "storage": storage},
        )
        LOG.debug("append_and_alias_pv response %s", response.json())
        result = cast(List[Dict[str, str]], response.json())
        if not check_result(result, f"Error while append_and_alias_pv {old}, {new}"):
            return
        LOG.debug("PV %s successfully appended and aliased to %s", old, new)


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
