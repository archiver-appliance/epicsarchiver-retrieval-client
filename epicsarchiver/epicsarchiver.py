"""Main module."""

from __future__ import annotations

from epicsarchiver.retrieval.client.archiver_retrieval import (
    ArchiverRetrieval,
)


class ArchiverAppliance(ArchiverRetrieval):
    """EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname
        port: EPICS Archiver Appliance retrieval port

    Examples:

    .. code-block:: python

        from epicsarchiver import ArchiverAppliance

        archappl = ArchiverAppliance("archiver-01.tn.esss.lu.se")
        print(archappl.version)
        archappl.get_pv_status(pv="BPM*")
        df = archappl.get_data("my:pv", start="2018-07-04 13:00", end=datetime.utcnow())
    """
