# -*- coding: utf-8 -*-
"""Utility functions"""
import datetime
from dateutil import parser


def format_date(date_or_str):
    """Return a string representing the date and time in ISO 8601 format

    :param date_or_str: can be a datetime object or string
                        if a string is given, it will be parsed automatically.
                        Timezone is ignored. UTC is always assumed.
    :return: string in ISO 8601 format
    """
    if not isinstance(date_or_str, datetime.datetime):
        dt = parser.parse(date_or_str, ignoretz=True)
    else:
        dt = date_or_str
    return dt.isoformat(timespec="microseconds") + 'Z'
