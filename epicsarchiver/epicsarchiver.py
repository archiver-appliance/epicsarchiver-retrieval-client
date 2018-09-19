# -*- coding: utf-8 -*-
"""Main module."""
import urllib.parse
import requests
import pandas as pd
from . import utils


class ArchiverAppliance:
    """EPICS Arcvhier Appliance client

    Hold a session to the Archiver Appliance web application.

    :param hostname: EPICS Archiver Appliance hostname [default: localhost]
    :param port: EPICS Archiver Appliance management port [default: 17665]

    Basic Usage::

        >>> from epicsarchiver import ArchiverAppliance
        >>> archappl = ArchiverAppliance('archiver-01.tn.esss.lu.se')
        >>> print(archapp.version)
        >>> archapp.get_pv_status(pv='BPM*')
        >>> df = archapp.get_data('my:pv', start='2018-07-04 13:00', end=datetime.utcnow())
    """

    def __init__(self, hostname="localhost", port=17665):
        self.hostname = hostname
        self.mgmt_url = f"http://{hostname}:{port}/mgmt/bpl/"
        self._info = None
        self._data_url = None
        self.session = requests.Session()

    def request(self, method, *args, **kwargs):
        """Sends a request using the session

        :param method: HTTP method
        :param \*args: Optional arguments
        :param \*\*kwargs: Optional keyword arguments
        :return: :class:`requests.Response <Response>` object
        """
        r = self.session.request(method, *args, **kwargs)
        r.raise_for_status()
        return r

    def get(self, endpoint, **kwargs):
        """Send a GET request to the given endpoint

        :param endpoint: API endpoint (relative or absolute)
        :param \*\*kwargs: Optional arguments to be sent
        :return: :class:`requests.Response <Response>` object
        """
        url = urllib.parse.urljoin(self.mgmt_url, endpoint.lstrip("/"))
        return self.request("GET", url, **kwargs)

    def post(self, endpoint, **kwargs):
        """Send a POST request to the given endpoint

        :param endpoint: API endpoint (relative or absolute)
        :param \*\*kwargs: Optional arguments to be sent
        :return: :class:`requests.Response <Response>` object
        """
        url = urllib.parse.urljoin(self.mgmt_url, endpoint.lstrip("/"))
        return self.request("POST", url, **kwargs)

    @property
    def info(self):
        """EPICS Archiver Appliance information"""
        if self._info is None:
            # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetApplianceInfo.html
            r = self.get("/getApplianceInfo")
            self._info = r.json()
        return self._info

    @property
    def identity(self):
        """EPICS Archiver Appliance identity"""
        return self.info.get("identity")

    @property
    def version(self):
        """EPICS Archiver Appliance version"""
        return self.info.get("version")

    @property
    def data_url(self):
        """EPICS Archiver Appliance data retrieval url"""
        if self._data_url is None:
            retrieval_url = self.info.get("dataRetrievalURL") + "/data/getData.json"
            # The Archiver Appliance always returns the server hostname.
            # We might want the FQDN or an IP. Use the hostname specified
            # to initialize the instance.
            parsed = urllib.parse.urlparse(retrieval_url)
            if parsed.port is None:
                netloc = self.hostname
            else:
                netloc = f"{self.hostname}:{parsed.port}"
            parsed_new_hostname = parsed._replace(netloc=netloc)
            self._data_url = urllib.parse.urlunparse(parsed_new_hostname)
        return self._data_url

    def get_all_expanded_pvs(self):
        """Return all expanded PV names in the cluster.

        This is targeted at automation and should return the PVs
        being archived, the fields, .VAL's, aliases and PV's in
        the archive workflow.
        Note this call can return 10's of millions of names.

        :return: list of expanded PV names
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetAllExpandedPVNames.html
        r = self.get("/getAllExpandedPVNames")
        return r.json()

    def get_all_pvs(self, pv=None, regex=None, limit=500):
        """Return all the PVs in the cluster

        :param pv: An optional argument that can contain a GLOB wildcard.
                   Will return PVs that match this GLOB.
                   For example: pv=KLYS*
        :param regex: An optional argument that can contain a Java regex \
                      wildcard.
                      Will return PVs that match this regex.
        :param limit: number of matched PV's that are returned.
                      To get all the PV names, (potentially in the millions),
                      set limit to –1. Default to 500.
        :return: list of PV names
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetAllPVs.html
        params = {"limit": limit}
        if pv is not None:
            params["pv"] = pv
        if regex is not None:
            params["regex"] = regex
        r = self.get("/getAllPVs", params=params)
        return r.json()

    def get_pv_status(self, pv):
        """Return the status of a PV

        :param pv: name(s) of the pv for which the status is to be determined.
                   Can be a GLOB wildcards or multiple PVs as a comma separated list.
        :return: list of dict with the status of the matching PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetPVStatusAction.html
        r = self.get("/getPVStatus", params={"pv": pv})
        return r.json()

    def archive_pv(self, pv, **kwargs):
        """Archive a PV

        :param pv: name of the pv to be achived.
                   Can be a comma separated list of names.
        :param \*\*kwargs: optional extra keyword arguments
            - samplingperiod
            - samplingmethod
            - controllingPV
            - policy
            - appliance
        :return: list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ArchivePVAction.html
        params = {"pv": pv}
        params.update(kwargs)
        r = self.get("/archivePV", params=params)
        return r.json()

    def archive_pvs(self, pvs):
        """Archive a list of PVs

        :param pvs: list of PVs (as dict) to archive
        :return: list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ArchivePVAction.html
        r = self.post("/archivePV", json=pvs)
        return r.json()

    def archive_pvs_from_files(self, files):
        """Archive PVs from a list of files

        :param files: list of files in CSV format with PVs to archive.
        :return: list of submitted PVs
        """
        pvs = utils.get_pvs_from_files(files)
        return self.archive_pvs(pvs)

    def _get_or_post(self, endpoint, pv):
        """Send a GET or POST if pv is a comma separated list

        :param endpoint: API endpoint
        :param pv: name of the pv.
                   Can be a GLOB wildcards or a list of comma separated names.
        :return: list of submitted PVs
        """
        if "," in pv:
            r = self.post(endpoint, data=pv)
        else:
            r = self.get(endpoint, params={"pv": pv})
        return r.json()

    def pause_pv(self, pv):
        """Pause the archiving of a PV(s)

        :param pv: name of the pv.
                   Can be a GLOB wildcards or a list of comma separated names.
        :return: list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/PauseArchivingPV.html
        return self._get_or_post("/pauseArchivingPV", pv)

    def resume_pv(self, pv):
        """Resume the archiving of a PV(s)

        :param pv: name of the pv.
                   Can be a GLOB wildcards or a list of comma separated names.
        :return: list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ResumeArchivingPV.html
        return self._get_or_post("/resumeArchivingPV", pv)

    def abort_pv(self, pv):
        """Abort any pending requests for archiving this PV.

        :param pv: name of the pv.
        :return: list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/AbortArchiveRequest.html
        r = self.get("/abortArchivingPV", params={"pv": pv})
        return r.json()

    def delete_pv(self, pv, delete_data=False):
        """Stop archiving the specified PV.

        The PV needs to be paused first.

        :param pv: name of the pv.
        :param delete_data: delete the data that has already been recorded.
                            Default to False.
        :return: list of submitted PVs
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/DeletePV.html
        r = self.get("/deletePV", params={"pv": pv, "delete_data": delete_data})
        return r.json()

    def update_pv(self, pv, samplingperiod, samplingmethod=None):
        """Change the archival parameters for a PV

        :param pv: name of the pv.
        :param samplingperiod: the new sampling period in seconds.
        :param samplingmethod: the new sampling method [SCAN|MONITOR]
        :return: list of submitted PV
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/ChangeArchivalParamsAction.html
        params = {"pv": pv, "samplingperiod": samplingperiod}
        if samplingmethod:
            params["samplingmethod"] = samplingmethod
        r = self.get("/changeArchivalParameters", params=params)
        return r.json()

    def get_data(self, pv, start, end):
        """Retrieve archived data

        :param pv: name of the pv.
        :param start: start time. Can be a string or `datetime.datetime` object.
        :param end: end time. Can be a string or `datetime.datetime` object.
        :return: `pandas.DataFrame`
        """
        # http://slacmshankar.github.io/epicsarchiver_docs/userguide.html
        params = {
            "pv": pv,
            "from": utils.format_date(start),
            "to": utils.format_date(end),
        }
        r = self.get(self.data_url, params=params)
        data = r.json()
        df = pd.DataFrame(data[0]["data"])
        try:
            df["date"] = pd.to_datetime(df["secs"] + df["nanos"] * 1e-9, unit="s")
        except KeyError:
            # Empty data
            pass
        else:
            df = df[["date", "val"]]
            df = df.set_index("date")
        return df
