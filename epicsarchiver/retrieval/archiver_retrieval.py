"""Archiver Retrieval methods."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

import pandas as pd
from dateutil import parser

from epicsarchiver.common.base_archiver import BaseArchiverAppliance
from epicsarchiver.retrieval.archive_event import ArchiveEvent, dataframe_from_events
from epicsarchiver.retrieval.pb import parse_pb_data

if TYPE_CHECKING:
    from requests import Response


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
