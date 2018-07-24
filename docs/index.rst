.. py-epicsarchiver documentation master file, created by
   sphinx-quickstart on Tue Jul 24 16:03:21 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to py-epicsarchiver's documentation!
============================================

Release v\ |version|.

Python package to interact with the `EPICS Archiver Appliance <https://slacmshankar.github.io/epicsarchiver_docs/>`_.

Quick start
-----------

::

    >>> from epicsarchiver import ArchiverAppliance
    >>> archiver = ArchiverAppliance("archiver-01.example.com")
    >>> print(archiver.version)
    >>> archiver.get_pv_status(pv='BPM*')
    >>> df = archiver.get_data('my:pv', start='2018-07-04 13:00', end=datetime.utcnow())
    
    >>> archiver.archive_pv("my:pv:name")


Please use the navigation sidebar on the left to begin.

.. toctree::
   :hidden:
   :maxdepth: 2

   installation
   command
   api
   changelog
