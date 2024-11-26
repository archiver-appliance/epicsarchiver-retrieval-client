"""Tests for archiver mgmt operations module."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest
import responses
from requests import HTTPError

from epicsarchiver.mgmt.archiver_mgmt_info import ArchivingStatus
from epicsarchiver.mgmt.archiver_mgmt_operations import (
    ArchiverMgmtOperations,
    Storage,
    check_result,
)

if TYPE_CHECKING:
    from pathlib import Path

LOG: logging.Logger = logging.getLogger(__name__)

TEST_DOMAIN = "archiver.example.org"


@responses.activate
def test_archive_pv() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = [
        {"pvName": "ISrc-010:HVAC-HT:AmbHumR", "status": "Archive request submitted"},
    ]
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/archivePV?pv=ISrc-010%3AHVAC-HT%3AAmbHumR",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.archive_pv("ISrc-010:HVAC-HT:AmbHumR")
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_archive_pv_with_extra_args() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = [
        {"pvName": "ISrc-010:HVAC-HT:AmbHumR", "status": "Archive request submitted"},
    ]
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/archivePV?pv=ISrc-010%3AHVAC-HT%3AAmbHumR&samplingperiod=2.0&samplingmethod=SCAN",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.archive_pv(
        "ISrc-010:HVAC-HT:AmbHumR",
        samplingperiod=2.0,
        samplingmethod="SCAN",
    )
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_archive_pvs() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = [{"pvName": "MY:PV", "status": "Already submitted"}]
    responses.add(
        responses.POST,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/archivePV",
        json=data,
        status=200,
    )
    pvs = [{"pv": "first:pv"}, {"pv": "second:pv"}]
    r = archiver.archive_pvs(pvs)
    assert len(responses.calls) == 1
    body_text = responses.calls[0].request.body
    assert body_text is not None
    body = json.loads(body_text)
    assert body == pvs
    assert r == data


@responses.activate
def test_archive_pvs_from_files(tmp_path: Path) -> None:
    # Create 2 files with some PVs
    pvs1 = [
        {"pv": "LEBT-010:PwrC-SolPS-01:CurS"},
        {"pv": "LEBT-010:ID-Iris:OFFSET_Y_SET"},
    ]
    tmp = tmp_path.joinpath("archiver01")
    tmp.mkdir()
    file1 = tmp.joinpath("file1.archive")
    file1.open("w").write("\n".join([item["pv"] for item in pvs1]))
    pvs2 = [{"pv": "LEBT-010:PBI-NPM-001:HCAM-COM", "policy": "slow"}]
    file2 = tmp.joinpath("file2")
    file2.open("w").write(pvs2[0]["pv"] + " " + pvs2[0]["policy"] + "\n")
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = [
        {"pvName": "LEBT-010:PBI-NPM-001:HCAM-COM", "status": "Already submitted"},
        {
            "pvName": "LEBT-010:ID-Iris:OFFSET_Y_SET",
            "status": "Archive request submitted",
        },
        {
            "pvName": "LEBT-010:PwrC-SolPS-01:CurS",
            "status": "Archive request submitted",
        },
    ]
    responses.add(
        responses.POST,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/archivePV",
        json=data,
        status=200,
    )
    r = archiver.archive_pvs_from_files([str(file1), str(file2)])
    assert len(responses.calls) == 1
    body_text = responses.calls[0].request.body
    assert body_text is not None
    body = json.loads(body_text)
    assert body == pvs1 + pvs2
    assert r == data
    # With appliance as parameter
    archiver.archive_pvs_from_files(
        [str(file1), str(file2)],
        appliance="appliance0",
    )  # ignore for https://github.com/getsentry/responses/pull/690

    body_text = responses.calls[1].request.body
    assert body_text is not None
    body = json.loads(body_text)
    pvs = pvs1 + pvs2
    for pv in pvs:
        pv["appliance"] = "appliance0"
    assert body == pvs


@responses.activate
def test_pause_pv_single() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = [
        {
            "pvName": "MY:PV",
            "engine_desc": "Successfully paused the archiving of PV MY:PV",
            "engine_pvName": "MY:PV",
            "engine_status": "ok",
            "etl_status": "ok",
            "etl_desc": "Successfully removed PV MY:PV from the cluster",
            "etl_pvName": "MY:PV",
            "status": "ok",
        },
    ]

    pv = "KLYS*"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/pauseArchivingPV?pv={pv}",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.pause_pv(pv)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_pause_pv_comma_separated_list() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = [{"validation": "Unable to pause PV MY:PV"}]
    pvs = "mypv1,mypv2"
    responses.add(
        responses.POST,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/pauseArchivingPV",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.pause_pv(pvs)
    assert (
        len(responses.calls) == 1
    )  # ignore for https://github.com/getsentry/responses/pull/690

    assert responses.calls[0].request.body == pvs
    assert r == data


@responses.activate
def test_resume_pv_single() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = [{"validation": "Unable to resume PV MY:PV"}]
    pv = "KLYS*"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/resumeArchivingPV?pv={pv}",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.resume_pv(pv)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_resume_pv_comma_separated_list() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = [
        {"validation": "Unable to pause PV mypv1"},
        {"validation": "Unable to pause PV mypv2"},
    ]
    pvs = "mypv1,mypv2"
    responses.add(
        responses.POST,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/resumeArchivingPV",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.resume_pv(pvs)
    assert (
        len(responses.calls) == 1
    )  # ignore for https://github.com/getsentry/responses/pull/690

    assert responses.calls[0].request.body == pvs
    assert r == data


@responses.activate
def test_abort_pv() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = ["1", "2", "3"]
    pv = "LEBT-010:PBI-NPM-001:HCAM-COM"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/abortArchivingPV?pv=LEBT-010%3APBI-NPM-001%3AHCAM-COM",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.abort_pv(pv)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_delete_pv_data_false() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = ["1", "2", "3"]
    pv = "LEBT-010:PBI-NPM-001:HCAM-COM"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/deletePV?pv=LEBT-010%3APBI-NPM-001%3AHCAM-COM&delete_data=False",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.delete_pv(pv)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_delete_pv_data_true() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = ["1", "2", "3"]
    pv = "LEBT-010:PBI-NPM-001:HCAM-COM"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/deletePV?pv=LEBT-010%3APBI-NPM-001%3AHCAM-COM&delete_data=True",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.delete_pv(pv, delete_data=True)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_update_pv() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = ["1", "2", "3"]
    pv = "mypv"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/changeArchivalParameters?pv={pv}&samplingperiod=2.0",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.update_pv(pv, 2.0)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_update_pv_samplingmethod() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    data = ["1", "2", "3"]
    pv = "mypv"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/changeArchivalParameters?pv={pv}&samplingperiod=2.0&samplingmethod=SCAN",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.update_pv(pv, 2.0, "SCAN")
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_pause_rename_resume_pv(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={pv}",
        json=[{"status": ArchivingStatus.BeingArchived}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={newname}",
        json=[{"status": ArchivingStatus.NotBeingArchived}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/pauseArchivingPV?pv={pv}",
        json={"status": "ok"},
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/renamePV?pv={pv}&newname={newname}",
        json={"status": "ok"},
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/resumeArchivingPV?pv={newname}",
        json={"status": "ok"},
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.pause_rename_resume_pv(pv, newname)
    captured_log = caplog.text
    assert len(responses.calls) == 5
    assert f"PV {pv} successfully renamed to {newname}\n" in captured_log


@responses.activate
def test_pause_rename_resume_pv_not_archived_pv(
    caplog: pytest.LogCaptureFixture,
) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={pv}",
        json=[{"status": ArchivingStatus.NotBeingArchived}],
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.pause_rename_resume_pv(pv, newname)
    captured_log = caplog.text
    assert len(responses.calls) == 1
    assert f"PV {pv} isn't being archived. Skipping.\n" in captured_log


@responses.activate
def test_pause_rename_resume_pv_existing_new(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={pv}",
        json=[{"status": ArchivingStatus.BeingArchived}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={newname}",
        json=[{"status": ArchivingStatus.BeingArchived}],
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.pause_rename_resume_pv(pv, newname)
    captured_log = caplog.text
    assert len(responses.calls) == 2
    assert f"New PV {newname} already exists. Skipping.\n" in captured_log


@responses.activate
def test_pause_rename_resume_pv_error_rename(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={pv}",
        json=[{"status": ArchivingStatus.BeingArchived}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={newname}",
        json=[{"status": ArchivingStatus.NotBeingArchived}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/pauseArchivingPV?pv={pv}",
        json={"status": "ok"},
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/renamePV?pv={pv}&newname={newname}",
        json={"validation": "error during rename"},
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.pause_rename_resume_pv(pv, newname)
    captured_log = caplog.text
    LOG.info(captured_log)
    assert len(responses.calls) == 4
    assert "error during rename" in captured_log


@responses.activate
def test_add_alias_ok(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/addAlias?pv={pv}&aliasname={newname}",
        json={"status": "ok", "desc": f"Added an alias {newname} for PV {pv}"},
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.add_alias(pv, newname)
    captured_log = caplog.text
    assert len(responses.calls) == 1
    assert f"Added an alias {newname} for PV {pv}" in captured_log


@responses.activate
def test_add_alias_pv_does_not_exist() -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/addAlias?pv={pv}&aliasname={newname}",
        status=500,
        match_querystring=True,
    )
    with pytest.raises(HTTPError):
        archiver.add_alias(pv, newname)


@responses.activate
def test_rename_and_append_success(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    old = "MY:PV"
    new = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={old}",
        json=[{"status": ArchivingStatus.Paused}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={new}",
        json=[{"status": ArchivingStatus.Paused}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/appendAndAliasPV?olderpv={old}&newerpv={new}&storage=MTS",
        json={
            "addAlias": "ok",
            "deleteOlder": "ok",
            "deleteNewer": "ok",
            "status": "ok",
        },
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.rename_and_append(old, new, Storage.MTS)
    captured_log = caplog.text
    assert len(responses.calls) == 3
    assert f"PV {old} successfully appended and aliased to {new}\n" in captured_log


@responses.activate
def test_rename_and_append_fail_not_archived_pv(
    caplog: pytest.LogCaptureFixture,
) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    old = "MY:PV"
    new = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={old}",
        json=[{"status": ArchivingStatus.NotBeingArchived}],
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.rename_and_append(old, new, Storage.MTS)
    captured_log = caplog.text
    assert len(responses.calls) == 1
    assert f"PV {old} isn't paused. Skipping.\n" in captured_log


@responses.activate
def test_rename_and_append_fail_pv_not_paused(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    old = "MY:PV"
    new = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={old}",
        json=[{"status": ArchivingStatus.Paused}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={new}",
        json=[{"status": ArchivingStatus.NotBeingArchived}],
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.rename_and_append(old, new, Storage.MTS)
    captured_log = caplog.text
    assert len(responses.calls) == 2
    assert f"PV {new} isn't paused. Skipping.\n" in captured_log


@responses.activate
def test_rename_and_append_fail_pv_error_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    archiver = ArchiverMgmtOperations(TEST_DOMAIN)
    old = "MY:PV"
    new = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={old}",
        json=[{"status": ArchivingStatus.Paused}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv={new}",
        json=[{"status": ArchivingStatus.Paused}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/appendAndAliasPV?olderpv={old}&newerpv={new}&storage=MTS",
        json={"validation": "error during appendAndAliasPV"},
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.rename_and_append(old, new, Storage.MTS)
    captured_log = caplog.text
    LOG.info(captured_log)
    assert len(responses.calls) == 3
    assert "error during appendAndAliasPV" in captured_log


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [({"status": "ok"}, True), ({"status": "foo"}, False), ({"hello": "world"}, False)],
)
def test_check_result(
    test_input: dict[str, str],
    expected: bool,  # noqa: FBT001
) -> None:
    output = check_result(test_input)
    assert output is expected


@pytest.mark.parametrize(
    ("test_input", "default_message", "output"),
    [
        ({"status": "nok"}, "Not OK", "Not OK\n"),
        ({"validation": "Hello"}, None, "Hello\n"),
        ({"validation": "Hello"}, "foo", "Hello\n"),
    ],
)
def test_check_result_message(
    caplog: pytest.LogCaptureFixture,
    test_input: dict[str, str],
    default_message: str,
    output: str,
) -> None:
    with caplog.at_level(logging.ERROR):
        check_result(test_input, default_message)
    captured_log = caplog.text
    assert output in captured_log
