"""Tests for `epicsarchiver.statistics.configuration` package."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockFixture

from epicsarchiver.statistics.configuration import ConfigOptions, get_not_configured
from epicsarchiver.statistics.models.stat_responses import (
    ConfiguredStatus,
    NoConfigResponse,
)
from epicsarchiver.statistics.services.archiver_statistics import (
    ArchiverWrapper,
)
from epicsarchiver.statistics.services.channelfinder import ChannelFinder

SAMPLES_PATH = Path(__file__).parent.resolve() / "samples"


@pytest.mark.asyncio
async def test_get_not_configured(mocker: MockFixture) -> None:
    archiver = ArchiverWrapper("archiver.example.org")
    channelfinder = ChannelFinder("channelfinder.example.org")
    mocker.patch(
        "epicsarchiver.mgmt.archiver_mgmt.ArchiverMgmt.get_all_pvs",
        return_value=["MY:PV", "MY:PV2"],
    )
    mocker.patch(
        "epicsarchiver.statistics._external_stats.get_all_non_paused_pvs",
        side_effect=AsyncMock(return_value={"MY:PV", "MY:PV2"}),
    )
    mocker.patch(
        "epicsarchiver.statistics.configuration.get_aliases",
        side_effect=AsyncMock(return_value={"MY:PV": [], "MY:PV3": ["MY:PV"]}),
    )
    mocker.patch(
        "epicsarchiver.statistics.services.gitlab.Gitlab.get_tar_ball",
        return_value=SAMPLES_PATH,
    )
    pvs_response = await get_not_configured(
        archiver, channelfinder, ConfigOptions(Path(), None)
    )
    assert {
        NoConfigResponse("MY:PV", ConfiguredStatus.Archived, [], []),
        NoConfigResponse(
            "MY:PV3", ConfiguredStatus.ConfiguredGitlab, ["MY:PV"], ["MY:PV"]
        ),
    } == set(pvs_response)
    await archiver.close()
    await channelfinder.close()
