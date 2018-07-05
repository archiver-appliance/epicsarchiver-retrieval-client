# -*- coding: utf-8 -*-
"""Tests for `epicsarchiver` package."""
from epicsarchiver import ArchiverAppliance


def test_epicsarchiver_url():
    """Test the CLI."""
    archiver = ArchiverAppliance()
    assert archiver.mgmt_url == "http://localhost:17665/mgmt/bpl/"
    archiver = ArchiverAppliance("archiver-01.example.com", port=80)
    assert archiver.mgmt_url == "http://archiver-01.example.com:80/mgmt/bpl/"
