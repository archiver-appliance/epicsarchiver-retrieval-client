.. py-epicsarchiver documentation master file, created by
   sphinx-quickstart on Tue Jul 24 16:03:21 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

py-epicsarchiver's documentation
================================

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

.. image:: https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver/badges/master/pipeline.svg
    :target: https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver

.. image:: https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver/badges/master/coverage.svg
    :target: https://gitlab.esss.lu.se/ics-infrastructure/py-epicsarchiver

Release v\ |release|.

Python package to interact with the `EPICS Archiver Appliance <https://slacmshankar.github.io/epicsarchiver_docs/>`_.

Quick start
-----------

::

    >>> from epicsarchiver import ArchiverAppliance
    >>> archiver = ArchiverAppliance("archiver-01.example.com")
    >>> print(archiver.version)

    >>> status = archiver.get_pv_status("ISrc-010:HVAC-HT:*")
    >>> pprint(status)
    [{'appliance': 'appliance0',
      'connectionFirstEstablished': 'Sep/13/2018 08:52:28 +02:00',
      'connectionLastRestablished': 'Sep/20/2018 08:00:02 +02:00',
      'connectionLossRegainCount': '178',
      'connectionState': 'true',
      'isMonitored': 'true',
      'lastEvent': 'Sep/20/2018 08:24:06 +02:00',
      'lastRotateLogs': 'Never',
      'pvName': 'ISrc-010:HVAC-HT:AmbHumR',
      'pvNameOnly': 'ISrc-010:HVAC-HT:AmbHumR',
      'samplingPeriod': '1.0',
      'status': 'Being archived'}]

    >>> df = archiver.get_data("ISrc-010:HVAC-HT:AmbHumR", "20180919 14:00", datetime(2018, 9, 19, 14, 5))
    >>> df.head()
                                         val
    date
    2018-09-19 13:59:53.891655207  48.210089
    2018-09-19 14:00:04.753609419  48.139897
    2018-09-19 14:00:04.755652666  48.136845
    2018-09-19 14:00:04.757656813  48.127689
    2018-09-19 14:00:04.759651423  48.155156
    
    >>> archiver.archive_pv("my:pv:name")


Please use the navigation sidebar on the left to begin.

.. toctree::
   :hidden:
   :maxdepth: 2

   installation
   command
   api
   changelog
