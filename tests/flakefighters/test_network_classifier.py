"""
This module tests the NetworkClassifier flakefighter.
"""

import json
from pathlib import Path

import pytest

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    Test,
    TestExecution,
)
from pytest_flakefighters.flakefighters.network_classifier import NetworkClassifier


def _report_path_from_command(command: list[str]) -> Path:
    """
    Extract the --json-report-file path from a constructed pytest command.
    """
    prefix = "--json-report-file="
    for arg in command:
        if arg.startswith(prefix):
            return Path(arg[len(prefix):])
    raise AssertionError("--json-report-file not found in command")


def _write_report(path: Path, entries: list[tuple[str, str, str]]):
    """
    Write a minimal pytest-json-report-shaped report file for a rerun.
    :param entries: List of (nodeid, outcome, longrepr) tuples for each test.
    """
    tests = [
        {
            "nodeid": nodeid,
            "outcome": outcome,
            "call": {"outcome": outcome, "longrepr": longrepr},
        }
        for nodeid, outcome, longrepr in entries
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump({"tests": tests}, file)


def _make_test(nodeid: str, outcomes: list[str]) -> Test:
    """
    Build a Test with one TestExecution per outcome given, representing the normal-run
    baseline for that test.
    """
    test = Test(name=nodeid)  # pylint: disable=E1123
    for outcome in outcomes:
        execution = TestExecution(outcome=outcome)  # pylint: disable=E1123
        test.executions.append(execution)
    return test


def test_timeout_must_be_positive():
    """
    Test that a non-positive timeout is rejected.
    """
    with pytest.raises(ValueError):
        NetworkClassifier(timeout=0)


def test_from_config_params():
    """
    Test that from_config generates the same result as a direct call.
    """
    from_config = NetworkClassifier.from_config(
        {
            "network_classifier_timeout": 15,
            "root": ".",
            "extra_pytest_args": ["-x"],
        }
    )
    init = NetworkClassifier(timeout=15, root=".", extra_pytest_args=["-x"])
    assert from_config.run_live == init.run_live
    assert from_config.params() == init.params()


def test_from_config_defaults():
    """
    Test that from_config falls back to sensible defaults when nothing is configured.
    """
    classifier = NetworkClassifier.from_config({})
    assert classifier.run_live is False
    assert classifier.timeout == NetworkClassifier.DEFAULT_TIMEOUT
    assert classifier.extra_pytest_args == []


def test_flaky_test_live_not_supported():
    """
    Test that flaky_test_live is not implemented, since this classifier needs the whole
    suite's baseline results before it can compare anything.
    """
    classifier = NetworkClassifier()
    with pytest.raises(NotImplementedError):
        classifier.flaky_test_live(None)


def test_confirmed_network_flaky(mocker):
    """
    Test that a test which passed normally, and confirmed fails with SocketBlockedError under
    the blocked-network run, is classified as flaky.
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()

    def fake_subprocess(command, cwd, env):  # pylint: disable=unused-argument
        report_path = _report_path_from_command(command)
        _write_report(
            report_path,
            [
                (
                    "tests/test_foo.py::test_bar",
                    "failed",
                    "pytest_socket.SocketBlockedError: A test tried to use socket.socket.",
                )
            ],
        )
        return "", ""

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_subprocess)
    classifier.flaky_tests_post(run)

    assert FlakefighterResult(name="NetworkClassifier", flaky=True) in test.flakefighter_results


def test_confirmed_network_flaky_via_connect_blocked(mocker):
    """
    Regression test: since --allow-hosts is configured, pytest-socket raises the distinct
    SocketConnectBlockedError when a test's connect() call
    is blocked
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()

    def fake_subprocess(command, cwd, env):  # pylint: disable=unused-argument
        report_path = _report_path_from_command(command)
        _write_report(
            report_path,
            [
                (
                    "tests/test_foo.py::test_bar",
                    "failed",
                    'pytest_socket.SocketConnectBlockedError: A test tried to use socket.socket.connect() '
                    'with host "8.8.8.8" (allowed: "127.0.0.1,::1,localhost (127.0.0.1)").',
                )
            ],
        )
        return "", ""

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_subprocess)
    classifier.flaky_tests_post(run)

    assert FlakefighterResult(name="NetworkClassifier", flaky=True) in test.flakefighter_results


def test_unconfirmed_failure_not_flaky(mocker):
    """
    Test that a failure NOT caused by a pytest-socket exception is not classified as
    network-flaky -- e.g. some other, unrelated failure that happened to occur on the rerun.
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()

    def fake_subprocess(command, cwd, env):  # pylint: disable=unused-argument
        report_path = _report_path_from_command(command)
        _write_report(
            report_path,
            [("tests/test_foo.py::test_bar", "failed", "AssertionError: expected 1 but got None")],
        )
        return "", ""

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_subprocess)
    classifier.flaky_tests_post(run)

    assert FlakefighterResult(name="NetworkClassifier", flaky=False) in test.flakefighter_results


def test_blocked_run_still_passes(mocker):
    """
    Test that a test which also passes under the blocked network run is not flaky.
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()

    def fake_subprocess(command, cwd, env):  # pylint: disable=unused-argument
        report_path = _report_path_from_command(command)
        _write_report(report_path, [("tests/test_foo.py::test_bar", "passed", "")])
        return "", ""

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_subprocess)
    classifier.flaky_tests_post(run)

    assert FlakefighterResult(name="NetworkClassifier", flaky=False) in test.flakefighter_results


def test_baseline_failure_skips_network_check_and_subprocess(mocker):
    """
    Test that a test which never passed normally is not classified as network-flaky
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["failed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()
    spy = mocker.patch.object(classifier, "_run_pytest_subprocess")

    classifier.flaky_tests_post(run)

    spy.assert_not_called()
    assert FlakefighterResult(name="NetworkClassifier", flaky=False) in test.flakefighter_results


def test_multiple_tests_classified_independently(mocker):
    """
    Test that each passed test in the suite is compared against its own entry in the
    blocked-network report, independently of the others
    """
    flaky_test = _make_test("tests/test_foo.py::test_flaky", outcomes=["passed"])
    stable_test = _make_test("tests/test_foo.py::test_stable", outcomes=["passed"])
    already_failed_test = _make_test("tests/test_foo.py::test_already_failed", outcomes=["failed"])
    run = Run(tests=[flaky_test, stable_test, already_failed_test])  # pylint: disable=E1123

    classifier = NetworkClassifier()
    captured_commands = []

    def fake_subprocess(command, cwd, env):  # pylint: disable=unused-argument
        captured_commands.append(command)
        report_path = _report_path_from_command(command)
        _write_report(
            report_path,
            [
                (
                    "tests/test_foo.py::test_flaky",
                    "failed",
                    "pytest_socket.SocketBlockedError: A test tried to use socket.socket.",
                ),
                ("tests/test_foo.py::test_stable", "passed", ""),
            ],
        )
        return "", ""

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_subprocess)
    classifier.flaky_tests_post(run)

    assert FlakefighterResult(name="NetworkClassifier", flaky=True) in flaky_test.flakefighter_results
    assert FlakefighterResult(name="NetworkClassifier", flaky=False) in stable_test.flakefighter_results
    assert FlakefighterResult(name="NetworkClassifier", flaky=False) in already_failed_test.flakefighter_results

    command = captured_commands[0]
    assert "tests/test_foo.py::test_flaky" in command
    assert "tests/test_foo.py::test_stable" in command
    assert "tests/test_foo.py::test_already_failed" not in command


def test_timeout_treated_as_inconclusive(mocker):
    """
    Test that a rerun timeout (signalled by None) is treated as inconclusive.
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()
    mocker.patch.object(classifier, "_run_pytest_subprocess", return_value=None)

    classifier.flaky_tests_post(run)

    assert FlakefighterResult(name="NetworkClassifier", flaky=False) in test.flakefighter_results


def test_missing_report_file_treated_as_inconclusive(mocker):
    """
    Test that a subprocess which ran but produced no report file is treated as inconclusive.
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()
    mocker.patch.object(classifier, "_run_pytest_subprocess", return_value=("", ""))

    classifier.flaky_tests_post(run)

    assert FlakefighterResult(name="NetworkClassifier", flaky=False) in test.flakefighter_results


def test_test_missing_from_blocked_report_treated_as_inconclusive(mocker):
    """
    Test that a test present in the baseline but absent from the blocked network report is
    treated as inconclusive for that test.
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()

    def fake_subprocess(command, cwd, env):  # pylint: disable=unused-argument
        report_path = _report_path_from_command(command)
        _write_report(report_path, [("tests/test_foo.py::some_other_test", "passed", "")])
        return "", ""

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_subprocess)
    classifier.flaky_tests_post(run)

    assert FlakefighterResult(name="NetworkClassifier", flaky=False) in test.flakefighter_results


def test_subprocess_disables_flakefighters_plugin_by_correct_name(mocker):
    """
    Test that the blocked rerun disables FlakeFighters to prevent recursive execution.
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier()
    captured_commands = []

    def fake_subprocess(command, cwd, env):  # pylint: disable=unused-argument
        captured_commands.append(command)
        report_path = _report_path_from_command(command)
        _write_report(report_path, [("tests/test_foo.py::test_bar", "passed", "")])
        return "", ""

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_subprocess)
    classifier.flaky_tests_post(run)

    command = captured_commands[0]
    assert "no:flakefighters" in command
    assert "no:pytest_flakefighters" not in command
    assert "--no-save" not in command  # would be rejected: unrecognized without the plugin loaded
    assert "--disable-socket" in command
    assert "--allow-unix-socket" in command
    assert "--allow-hosts=localhost,127.0.0.1,::1" in command
    assert "tests/test_foo.py::test_bar" in command


def test_subprocess_uses_project_root_as_cwd(mocker, tmp_path):
    """
    Test that the blocked network run subprocess is executed with the classifier's root as
    its working directory, so nodeid resolution matches the project layout.
    """
    test = _make_test("tests/test_foo.py::test_bar", outcomes=["passed"])
    run = Run(tests=[test])  # pylint: disable=E1123

    classifier = NetworkClassifier(root=str(tmp_path))
    captured = {}

    def fake_subprocess(command, cwd, env):  # pylint: disable=unused-argument
        captured["cwd"] = cwd
        report_path = _report_path_from_command(command)
        _write_report(report_path, [("tests/test_foo.py::test_bar", "passed", "")])
        return "", ""

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_subprocess)
    classifier.flaky_tests_post(run)

    assert captured["cwd"] == str(tmp_path)
