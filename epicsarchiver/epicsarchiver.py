"""Main module."""

from __future__ import annotations

import datetime
import logging
import urllib.parse
from pathlib import Path
from typing import Any, cast

import pandas as pd
import requests
from dateutil import parser
from requests import Response

from epicsarchiver import archive_files
from epicsarchiver.archive_event import ArchiveEvent, dataframe_from_events
from epicsarchiver.pb import parse_pb_data
from epicsarchiver.statistics.stat_responses import (
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    LostConnectionsResponse,
    PausedPVResponse,
    SilentPVsResponse,
    StorageRatesResponse,
)

LOG: logging.Logger = logging.getLogger(__name__)


class BaseArchiverAppliance:
    """Base EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname [default: localhost]
        port: EPICS Archiver Appliance management port [default: 17665]
    """

    def __init__(self, hostname: str = "localhost", port: int = 17665):
        """Create Archiver Appliance object.

        Args:
            hostname (str, optional): hostname of archiver. Defaults to "localhost".
            port (int, optional): port number of mgmt interface. Defaults to 17665.
        """
        self.hostname = hostname
        self.mgmt_url = f"http://{hostname}:{port}/mgmt/bpl/"
        self._info: dict[str, str] = {}
        self._data_url: str | None = None
        self.session = requests.Session()

    def __repr__(self) -> str:
        """String representation of Archiver Appliance.

        Returns:
            str: details including hostname of Archiver appliance.
        """
        return f"ArchiverAppliance({self.hostname})"

    def _request(self, method: str, *args: Any, **kwargs: Any) -> Response:
        r"""Sends a request using the session.

        Args:
            method: HTTP method
            *args: Optional arguments
            **kwargs: Optional keyword arguments

        Returns:
            :class:`requests.Response <Response>` object
        """
        r = self.session.request(method, *args, **kwargs)
        r.raise_for_status()
        return r

    def _get(self, endpoint: str, **kwargs: Any) -> Response:
        r"""Send a GET request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            **kwargs: Optional arguments to be sent

        Returns:
            :class:`requests.Response <Response>` object
        """
        url = urllib.parse.urljoin(self.mgmt_url, endpoint.lstrip("/"))
        LOG.debug("GET url: %s", url)
        return self._request("GET", url, **kwargs)

    def _post(self, endpoint: str, **kwargs: Any) -> Response:
        r"""Send a POST request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            **kwargs: Optional arguments to be sent

        Returns:
            :class:`requests.Response <Response>` object
        """
        url = urllib.parse.urljoin(self.mgmt_url, endpoint.lstrip("/"))
        return self._request("POST", url, **kwargs)

    @property
    def info(self) -> dict[str, str]:
        """EPICS Archiver Appliance information."""
        if not self._info:
            # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetApplianceInfo.html
            r = self._get("/getApplianceInfo")
            self._info = r.json()
        return self._info

    @property
    def identity(self) -> str | None:
        """EPICS Archiver Appliance identity."""
        return self.info.get("identity")

    @property
    def version(self) -> str | None:
        """EPICS Archiver Appliance version."""
        return self.info.get("version")

    def _get_or_post(self, endpoint: str, pv: str) -> Any:
        """Send a GET or POST if pv is a comma separated list.

        Args:
            endpoint: API endpoint
            pv: name of the pv. Can be a GLOB wildcards or a list of
                comma separated names.

        Returns:
            list of submitted PVs
        """
        r = (
            self._post(endpoint, data=pv)
            if "," in pv
            else self._get(endpoint, params={"pv": pv})
        )
        return r.json()


def format_date(date_or_str: datetime.datetime | str) -> str:
    """Return a string representing the date and time in ISO 8601 format.

    Args:
        date_or_str: can be a datetime object or string if a string is
            given, it will be parsed automatically. Timezone is ignored.
            UTC is always assumed.

    Returns:
        string in ISO 8601 format
    """
    if not isinstance(date_or_str, datetime.datetime):
        dt = parser.parse(date_or_str, ignoretz=True)
    else:
        dt = date_or_str.replace(tzinfo=None)
    return dt.isoformat(timespec="microseconds") + "Z"


def json_to_dataframe(data: Any) -> pd.DataFrame:
    """Converts json from the archiver.

    Converts to a dataframe with two
    columns "date" and "val" and the index is "date".

    Args:
        data: json from a json archiver request

    Returns:
        pd.DataFrame
    """
    events_dataframe = pd.DataFrame(data[0]["data"])
    try:
        total_nanos = (
            events_dataframe["secs"].multiply(1e9).add(events_dataframe["nanos"])
        )
        events_dataframe["date"] = pd.to_datetime(total_nanos, unit="ns", utc=True)
    except KeyError:
        # Empty data
        pass
    else:
        events_dataframe = events_dataframe[["date", "val"]]
        events_dataframe = events_dataframe.set_index("date")
    return events_dataframe


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
        return cast(list[str], r.json())

    def get_all_pvs(
        self,
        pv: str | None = None,
        regex: str | None = None,
        limit: int = 500,
    ) -> list[str]:
        """Return all the PVs in the cluster.

        Args:
            pv: An optional argument that can contain a GLOB wildcard.
                Will return PVs that match this GLOB. For example:
                pv=KLYS*
            regex: An optional argument that can contain a Java regex \
                wildcard. Will return PVs that match this regex.
            limit: number of matched PV's that are returned. To get all
                the PV names, (potentially in the millions), set limit
                to -1. Default to 500.

        Returns:
            list of PV names
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetAllPVs.html
        params: dict[str, str] = {"limit": str(limit)}
        if pv is not None:
            params["pv"] = pv
        if regex is not None:
            params["regex"] = regex
        r = self._get("/getAllPVs", params=params)
        return cast(list[str], r.json())

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
        return cast(list[dict[str, str]], r.json())

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
        return cast(list[dict[str, str]], r.json())

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
        return cast(list[str], r.json())

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
        return cast(list[dict[str, str]], r.json())

    def archive_pvs(self, pvs: list[dict[str, str]]) -> list[dict[str, str]]:
        """Archive a list of PVs.

        Args:
            pvs: list of PVs (as dict) to archive

        Returns:
            list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ArchivePVAction.html
        r = self._post("/archivePV", json=pvs)
        return cast(list[dict[str, str]], r.json())

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
            return cast(dict[str, str], response)
        return cast(list[dict[str, str]], response)

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
            return cast(dict[str, str], response)
        return cast(list[dict[str, str]], response)

    def abort_pv(self, pv: str) -> list[str]:
        """Abort any pending requests for archiving this PV.

        Args:
            pv: name of the pv.

        Returns:
            list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/AbortArchiveRequest.html
        r = self._get("/abortArchivingPV", params={"pv": pv})
        return cast(list[str], r.json())

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
        return cast(list[str], r.json())

    def rename_pv(self, pv: str, newname: str) -> dict[str, str]:
        """Rename this pv to a new name.

        The PV needs to be paused first.

        Args:
            pv: name of the pv.
            newname: new name of the pv

        Returns:
            list of submitted PVs
        """
        # https://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/RenamePVAction.html
        r = self._get("/renamePV", params={"pv": pv, "newname": newname})
        return cast(dict[str, str], r.json())

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
        return cast(list[str], r.json())

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


class ArchiverRetrieval(BaseArchiverAppliance):
    """Retrieval EPICS Archiver Appliance client.

    Hold a session to the Retrieval Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname [default: localhost]
        port: EPICS Archiver Appliance management port [default: 17665]

    Examples:
    .. code-block:: python

        from epicsarchiver.archiver.retrieval import ArchiverRetrieval

        archappl = ArchiverRetrieval("archiver-01.tn.esss.lu.se")
        print(archappl.version)
        df = archappl.get_data("my:pv", start="2018-07-04 13:00", end=datetime.utcnow())
    """

    def data_url(self) -> str:
        """EPICS Archiver Appliance data retrieval url."""
        if self._data_url is None:
            data_url_base = self.info.get("dataRetrievalURL")
            if data_url_base is None:
                raise ConnectionError
            self._data_url = data_url_base + "/data/getData.raw"
        return self._data_url

    def _get_data_raw(
        self,
        pv: str,
        start: str | datetime.datetime,
        end: str | datetime.datetime,
    ) -> Response:
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
            "from": format_date(start),
            "to": format_date(end),
        }
        return self._get(
            self.data_url(),
            params=params,
            stream=True,
        )

    def get_events(
        self,
        pv: str,
        start: str | datetime.datetime,
        end: str | datetime.datetime,
    ) -> list[ArchiveEvent]:
        """Retrieve archived data.

        Args:
            pv: name of the pv.
            start: start time. Can be a string or `datetime.datetime`
                object.
            end: end time. Can be a string or `datetime.datetime`
                object.

        Returns:
            `pandas.DataFrame`
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        r = self._get_data_raw(pv, start, end)
        pb_data = r.content
        return parse_pb_data(pb_data)

    def get_data(
        self,
        pv: str,
        start: str | datetime.datetime,
        end: str | datetime.datetime,
    ) -> pd.DataFrame:
        """Retrieve archived data.

        Args:
            pv: name of the pv.
            start: start time. Can be a string or `datetime.datetime`
                object.
            end: end time. Can be a string or `datetime.datetime`
                object.

        Returns:
            `pandas.DataFrame`
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        return dataframe_from_events(self.get_events(pv, start, end))


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


class ArchiverAppliance(ArchiverMgmt, ArchiverRetrieval, ArchiverStatistics):
    """EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname [default: localhost]
        port: EPICS Archiver Appliance management port [default: 17665]

    Examples:
    .. code-block:: python

        from epicsarchiver import ArchiverAppliance

        archappl = ArchiverAppliance("archiver-01.tn.esss.lu.se")
        print(archappl.version)
        archappl.get_pv_status(pv="BPM*")
        df = archappl.get_data("my:pv", start="2018-07-04 13:00", end=datetime.utcnow())
    """
