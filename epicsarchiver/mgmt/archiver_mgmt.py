"""ArchiverMgmt module."""

from __future__ import annotations

import logging

from epicsarchiver.mgmt.archiver_mgmt_info import ArchiverMgmtInfo

LOG: logging.Logger = logging.getLogger(__name__)


class ArchiverMgmt(ArchiverMgmtInfo):
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
