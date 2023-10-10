"""Tests for epicsarchiver.command module."""
from pathlib import Path

from click.testing import CliRunner
from pytest import CaptureFixture
from pytest_mock import MockerFixture

from epicsarchiver import command


def test_archive_file_does_not_exist() -> None:
    runner = CliRunner()
    files = ["file1", "file2"]
    result = runner.invoke(command.cli, ["archive", *files])
    assert result.exit_code == 2
    assert "Path 'file1' does not exist." in result.output


def test_archive_file_does_exist(
    tmp_path: Path, mocker: MockerFixture, capsys: CaptureFixture[str]
) -> None:
    mock_archiver = mocker.patch("epicsarchiver.command.ArchiverAppliance")
    file1 = tmp_path.joinpath("file1")
    file1.open("w").write("test")
    file2 = tmp_path.joinpath("file2")
    file2.open("w").write("test")
    runner = CliRunner()
    files = (str(file1), str(file2))
    with capsys.disabled():
        result = runner.invoke(command.cli, ["archive", *list(files)])
        assert result.exit_code == 0
        assert result.output == ""
        mock_archiver.return_value.archive_pvs_from_files.assert_called_once_with(
            files, None
        )
        mock_archiver.assert_called_once_with("localhost")


def test_archive_hostname(
    tmp_path: Path, mocker: MockerFixture, capsys: CaptureFixture[str]
) -> None:
    mock_archiver = mocker.patch("epicsarchiver.command.ArchiverAppliance")
    hostname = "myarchiver.example.org"
    file1 = tmp_path.joinpath("file1")
    file1.open("w").write("test")
    runner = CliRunner()
    with capsys.disabled():
        result = runner.invoke(
            command.cli, ["--hostname", hostname, "archive", str(file1)]
        )
        assert result.exit_code == 0
        mock_archiver.assert_called_once_with(hostname)


def test_archive_with_appliance(
    tmp_path: Path, mocker: MockerFixture, capsys: CaptureFixture[str]
) -> None:
    mock_archiver = mocker.patch("epicsarchiver.command.ArchiverAppliance")
    appliance = "foo"
    file1 = tmp_path.joinpath("file1")
    file1.open("w").write("test")
    runner = CliRunner()
    with capsys.disabled():
        result = runner.invoke(
            command.cli, ["archive", "--appliance", appliance, str(file1)]
        )
        assert result.exit_code == 0
        assert result.output == ""
        mock_archiver.return_value.archive_pvs_from_files.assert_called_once_with(
            (str(file1),), appliance
        )


def test_rename(tmp_path: Path, mocker: MockerFixture) -> None:
    mock_archiver = mocker.patch("epicsarchiver.command.ArchiverAppliance")
    hostname = "myarchiver.example.org"
    file1 = tmp_path.joinpath("file1")
    file1.open("w").write("test")
    file2 = tmp_path.joinpath("file2")
    file2.open("w").write("test2")
    runner = CliRunner()
    result = runner.invoke(
        command.cli, ["--hostname", hostname, "rename", str(file1), str(file2)]
    )
    assert result.exit_code == 0
    mock_archiver.return_value.rename_pvs_from_files.assert_called_once_with(
        (str(file1), str(file2))
    )
