# -*- coding: utf-8 -*-
"""Tests for epicsarchiver.command module."""
from click.testing import CliRunner
from epicsarchiver import command


def test_archive_file_does_not_exist():
    runner = CliRunner()
    files = ["file1", "file2"]
    result = runner.invoke(command.cli, ["archive"] + files)
    assert result.exit_code == 2
    assert 'Path "file1" does not exist.' in result.output


def test_archive_file_does_exist(tmpdir, mocker):
    mock_archiver = mocker.patch("epicsarchiver.command.ArchiverAppliance")
    file1 = tmpdir.join("file1")
    file1.write("test")
    file2 = tmpdir.join("file2")
    file2.write("test")
    runner = CliRunner()
    files = (str(file1), str(file2))
    result = runner.invoke(command.cli, ["archive"] + list(files))
    assert result.exit_code == 0
    assert result.output == ""
    mock_archiver.return_value.archive_pvs_from_files.assert_called_once_with(files)
    mock_archiver.assert_called_once_with("localhost")


def test_archive_hostname(tmpdir, mocker):
    mock_archiver = mocker.patch("epicsarchiver.command.ArchiverAppliance")
    hostname = "myarchiver.example.org"
    file1 = tmpdir.join("file1")
    file1.write("test")
    runner = CliRunner()
    result = runner.invoke(command.cli, ["--hostname", hostname, "archive", str(file1)])
    assert result.exit_code == 0
    mock_archiver.assert_called_once_with(hostname)
