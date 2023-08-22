# Changelog

## 0.5.0 (2023-08-23)
 * Swap json interface for protobuf interface
 * Add type hints

## 0.4.0 (2020-05-15)

* Remove dataRetrievalURL transformation
* Add get_unarchived_pvs method
* Add get_pv_status_from_files and get_unarchived_pvs_from_files methods
* Add rename_pv method and rename command (INFRA-2115)
* Add badges to README and documentation

## 0.3.0 (2018-11-22)

* Allow to force the policy via CSV files (INFRA-528)
* Allow to pass the appliance to be used in a cluster (INFRA-670)

## 0.2.0 (2018-09-20)

* Do not force sampling period and method
* Add proper tests

### Breaking changes

Passing samplingmethod and samplingperiod via the API to the archiver appliance overwrites what is returned from the site policies.py.
To avoid that, it was disabled:

* :meth:`epicsarchiver.ArchiverAppliance.archive_pvs_from_files` and :func:`epicsarchiver.utils.get_pvs_from_files`
  don't take period and method as arguments anymore.
* :func:`epicsarchiver.utils.get_pvs_from_files` only returns PV names. Sampling method and period (if present) are ignored.

## 0.1.0.post1 (2018-07-24)

* Add sphinx documentation

## 0.1.0 (2018-07-24)

* Initial release
