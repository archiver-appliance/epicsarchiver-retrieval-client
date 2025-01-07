"""Main module."""

from __future__ import annotations

from epicsarchiver.mgmt.archiver_mgmt import ArchiverMgmt
from epicsarchiver.retrieval.archiver_retrieval.archiver_retrieval import (
    ArchiverRetrieval,
)


class ArchiverAppliance(ArchiverMgmt, ArchiverRetrieval):
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
