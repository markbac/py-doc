"""The supported-platform rule: Linux and Windows only."""

from __future__ import annotations

import sys

import pytest

from py_doc import platform
from py_doc.errors import ConversionError, EnvironmentProblem, exit_status


@pytest.mark.parametrize(
    ("reported", "expected"),
    [("linux", "linux"), ("linux2", "linux"), ("win32", "windows"), ("darwin", "darwin"), ("freebsd14", "freebsd14")],
)
def test_current_names_the_platform(monkeypatch, reported, expected):
    monkeypatch.setattr("sys.platform", reported)
    assert platform.current() == expected


@pytest.mark.parametrize("reported", ["linux", "win32"])
def test_supported_platforms_pass(monkeypatch, reported):
    monkeypatch.setattr("sys.platform", reported)
    assert platform.require_supported() in platform.SUPPORTED


def test_macos_is_refused_with_a_message_naming_the_supported_platforms(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    with pytest.raises(EnvironmentProblem) as caught:
        platform.require_supported()
    assert "Linux and Windows" in str(caught.value)
    assert "macOS" in str(caught.value)


def test_environment_problems_exit_with_status_2_and_other_failures_with_1():
    assert exit_status(EnvironmentProblem("no engine")) == 2
    assert exit_status(ConversionError("bad input")) == 1
    assert exit_status(ValueError("bug")) == 1


def test_a_converter_that_hits_an_environment_problem_makes_the_command_exit_2(tmp_path):
    import argparse

    from py_doc._cli import convert_all

    class NeedsTools:
        def validate_template(self):
            pass

        def convert_file(self, md_path, output_path):
            raise EnvironmentProblem("no tool container")

    source = tmp_path / "a.md"
    source.write_text("# A\n", encoding="utf-8")
    args = argparse.Namespace(input=str(source), output=None)
    assert convert_all(NeedsTools(), args, ".docx", "Word") == 2


def test_restoring_the_console_does_nothing_off_windows(monkeypatch):
    from py_doc.platform import restore_console_input

    monkeypatch.setattr(sys, "platform", "linux")
    restore_console_input()  # no ctypes.windll here, and none needed


def test_a_raw_windows_console_is_put_back_into_line_mode(monkeypatch):
    import ctypes

    from py_doc.platform import restore_console_input

    calls = []

    class Kernel32:
        def GetStdHandle(self, which):
            return 7

        def GetConsoleMode(self, handle, mode):
            mode._obj.value = 0x0200  # raw: virtual terminal input only
            return 1

        def SetConsoleMode(self, handle, mode):
            calls.append((handle, mode))
            return 1

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", type("WinDLL", (), {"kernel32": Kernel32()})(), raising=False)
    restore_console_input()
    assert calls == [(7, 0x0200 | 0x0001 | 0x0002 | 0x0004)]
