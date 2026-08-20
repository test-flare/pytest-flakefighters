"""
This module tests the NetworkClassifier flakefighter.
"""

import json
from datetime import datetime, timedelta

import pytest

from pytest_flakefighters.database_management import (
    Run,
    Test,
    TestExecution,
)
from pytest_flakefighters.flakefighters.network_classifier import (
    NetworkClassifier,
)


def _execution(outcome, duration=None):
    """Create a test execution."""
    start = datetime(2026, 1, 1, 12, 0, 0)

    if duration is None:
        return TestExecution(
            outcome=outcome,
            start_time=None,
            end_time=None,
        )

    return TestExecution(
        outcome=outcome,
        start_time=start,
        end_time=start + timedelta(seconds=duration),
    )

def test_from_config_params():
    """Test config construction."""
    config = {
        "root": ".",
        "extra_pytest_args": ["-vv"],
    }

    from_config = NetworkClassifier.from_config(config)

    direct = NetworkClassifier(
        root=".",
        extra_pytest_args=["-vv"],
    )

    assert from_config.root == direct.root
    assert from_config.extra_pytest_args == direct.extra_pytest_args
    assert from_config.params() == direct.params()

def test_flaky_test_live_not_supported():
    """Test that live classification is not supported."""
    classifier = NetworkClassifier()

    with pytest.raises(NotImplementedError):
        classifier.flaky_test_live(
            TestExecution(outcome="passed")
        )

def test_longest_passed_duration():
    """Test longest passed duration."""
    test = Test(
        name="test_example",
        executions=[
            _execution("passed", 0.2),
            _execution("failed", 5.0),
            _execution("passed", 0.8),
        ],
    )

    classifier = NetworkClassifier()

    assert classifier._longest_passed_duration(test) == pytest.approx(0.8)

def test_longest_passed_duration_no_pass():
    """Test no passed execution."""
    test = Test(
        name="test_example",
        executions=[
            _execution("failed", 0.5),
            _execution("failed", 1.0),
        ],
    )

    classifier = NetworkClassifier()

    assert classifier._longest_passed_duration(test) is None

def test_longest_passed_duration_missing_times():
    """Test missing execution timestamps."""
    test = Test(
        name="test_example",
        executions=[
            _execution("passed"),
        ],
    )

    classifier = NetworkClassifier()

    assert classifier._longest_passed_duration(test) is None

def test_existing_pass_without_timing_is_still_eligible(mocker):
    test = Test(
        name="test_example",
        executions=[
            _execution("passed"),
        ],
    )

    run = Run(tests=[test])
    classifier = NetworkClassifier()

    baseline = mocker.patch.object(
        classifier,
        "_measure_own_baseline",
    )

    blocked = mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={
            "test_example": {
                "outcome": "passed",
            }
        },
    )

    classifier.flaky_tests_post(run)

    baseline.assert_not_called()

    blocked.assert_called_once_with(
        ["test_example"],
        pytest.approx(1.0),
    )
    
@pytest.mark.parametrize(
    ("durations", "expected"),
    [
        ([0.2, 0.8, 0.5], 2.4),
        ([0.1, 0.2], 1.0),
        ([], 1.0),
    ],
)
def test_compute_timeout(durations, expected):
    """Test timeout calculation."""
    classifier = NetworkClassifier()

    assert classifier._compute_timeout(durations) == pytest.approx(expected)

def test_subprocess_env(monkeypatch):
    """Test child process environment."""
    monkeypatch.setenv("PYTEST_ADDOPTS", "--some-option")
    monkeypatch.setenv("COVERAGE_FILE", "/tmp/.coverage")
    monkeypatch.setenv("KEEP_ME", "value")

    classifier = NetworkClassifier()

    env = classifier._subprocess_env()

    assert "PYTEST_ADDOPTS" not in env
    assert "COVERAGE_FILE" not in env
    assert env["KEEP_ME"] == "value"

def test_run_pytest_subprocess_success(mocker):
    """Test successful subprocess execution."""
    mocked_run = mocker.patch(
        "pytest_flakefighters.flakefighters."
        "network_classifier.subprocess.run"
    )

    classifier = NetworkClassifier()

    result = classifier._run_pytest_subprocess(
        ["pytest"],
        cwd=".",
        env={},
    )

    assert result is True
    mocked_run.assert_called_once()

def test_run_pytest_subprocess_oserror(mocker):
    """Test subprocess launch failure."""
    mocked_run = mocker.patch(
        "pytest_flakefighters.flakefighters."
        "network_classifier.subprocess.run"
    )
    mocked_run.side_effect = OSError("failed")

    classifier = NetworkClassifier()

    result = classifier._run_pytest_subprocess(
        ["pytest"],
        cwd=".",
        env={},
    )

    assert result is False

def test_report_socket_blocked():
    """Test SocketBlockedError detection."""
    classifier = NetworkClassifier()

    report = {
        "outcome": "failed",
        "call": {
            "outcome": "failed",
            "longrepr": (
                "pytest_socket.SocketBlockedError: "
                "socket disabled"
            ),
        },
    }

    assert classifier._report_confirms_socket_blocked(report)

def test_report_socket_connect_blocked():
    """Test SocketConnectBlockedError detection."""
    classifier = NetworkClassifier()

    report = {
        "outcome": "failed",
        "call": {
            "outcome": "failed",
            "crash": {
                "message": (
                    "pytest_socket.SocketConnectBlockedError: "
                    "blocked"
                )
            },
        },
    }

    assert classifier._report_confirms_socket_blocked(report)

def test_report_unrelated_failure():
    """Test unrelated failure."""
    classifier = NetworkClassifier()

    report = {
        "outcome": "failed",
        "call": {
            "outcome": "failed",
            "longrepr": "AssertionError",
        },
    }

    assert not classifier._report_confirms_socket_blocked(report)

def test_report_timeout():
    """Test timeout detection."""
    classifier = NetworkClassifier()

    report = {
        "outcome": "failed",
        "call": {
            "outcome": "failed",
            "longrepr": "Failed: Timeout >2.0s",
        },
    }

    assert classifier._report_confirms_timeout(report)

@pytest.mark.parametrize(
    "report",
    [
        {"outcome": "failed"},
        {"outcome": "error"},
        {
            "outcome": "passed",
            "setup": {"outcome": "failed"},
        },
        {
            "outcome": "passed",
            "call": {"outcome": "error"},
        },
        {
            "outcome": "passed",
            "teardown": {"outcome": "failed"},
        },
    ],
)
def test_report_failed(report):
    """Test failure detection."""
    classifier = NetworkClassifier()

    assert classifier._report_failed(report)

def test_report_passed():
    """Test passed report."""
    classifier = NetworkClassifier()

    report = {
        "outcome": "passed",
        "setup": {"outcome": "passed"},
        "call": {"outcome": "passed"},
        "teardown": {"outcome": "passed"},
    }

    assert not classifier._report_failed(report)

def test_measure_own_baseline_no_nodeids(mocker):
    """Test empty baseline request."""
    classifier = NetworkClassifier()

    subprocess_runner = mocker.patch.object(
        classifier,
        "_run_pytest_subprocess",
    )

    result = classifier._measure_own_baseline([])

    assert result == {}
    subprocess_runner.assert_not_called()

def test_measure_own_baseline_parses_report(mocker):
    """Test baseline report parsing."""
    classifier = NetworkClassifier()

    def fake_run(command, cwd, env):
        report_arg = next(
            arg
            for arg in command
            if arg.startswith("--json-report-file=")
        )

        report_path = report_arg.split("=", 1)[1]

        report = {
            "tests": [
                {
                    "nodeid": "test_a.py::test_a",
                    "outcome": "passed",
                    "setup": {"duration": 0.1},
                    "call": {"duration": 0.4},
                    "teardown": {"duration": 0.2},
                },
                {
                    "nodeid": "test_b.py::test_b",
                    "outcome": "failed",
                    "call": {
                        "outcome": "failed",
                        "longrepr": "AssertionError",
                    },
                },
            ]
        }

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(report, file)

        return True

    mocker.patch.object(
        classifier,
        "_run_pytest_subprocess",
        side_effect=fake_run,
    )

    measured = classifier._measure_own_baseline(
        [
            "test_a.py::test_a",
            "test_b.py::test_b",
        ]
    )

    assert measured["test_a.py::test_a"]["outcome"] == "passed"
    assert measured["test_a.py::test_a"]["duration"] == pytest.approx(
        0.7
    )

    assert measured["test_b.py::test_b"]["outcome"] == "failed"
    assert measured["test_b.py::test_b"]["duration"] is None

def test_measure_own_baseline_subprocess_failure(mocker):
    """Test baseline subprocess failure."""
    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_pytest_subprocess",
        return_value=False,
    )

    result = classifier._measure_own_baseline(
        ["test_a.py::test_a"]
    )

    assert result == {}

def test_run_with_disabled_socket_parses_report(mocker):
    """Test blocked-network report parsing."""
    classifier = NetworkClassifier()

    captured_command = {}

    def fake_run(command, cwd, env):
        captured_command["command"] = command

        report_arg = next(
            arg
            for arg in command
            if arg.startswith("--json-report-file=")
        )

        report_path = report_arg.split("=", 1)[1]

        report = {
            "tests": [
                {
                    "nodeid": "test_a.py::test_a",
                    "outcome": "failed",
                    "call": {
                        "outcome": "failed",
                        "longrepr": (
                            "pytest_socket.SocketBlockedError: "
                            "socket disabled"
                        ),
                    },
                }
            ]
        }

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(report, file)

        return True

    mocker.patch.object(
        classifier,
        "_run_pytest_subprocess",
        side_effect=fake_run,
    )

    reports = classifier._run_with_disabled_socket(
        ["test_a.py::test_a"],
        2.4,
    )

    command = captured_command["command"]

    assert "--disable-socket" in command
    assert "--allow-unix-socket" in command
    assert "--allow-hosts=localhost,127.0.0.1,::1" in command
    assert "--timeout=2.4" in command
    assert "-p" in command
    assert "no:flakefighters" in command

    assert reports["test_a.py::test_a"]["outcome"] == "failed"

def test_run_with_disabled_socket_subprocess_failure(mocker):
    """Test blocked subprocess failure."""
    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_pytest_subprocess",
        return_value=False,
    )

    result = classifier._run_with_disabled_socket(
        ["test_a.py::test_a"],
        2.0,
    )

    assert result is None

def test_existing_pass_is_eligible(mocker):
    """Test reuse of an existing passing execution."""
    test = Test(
        name="test_example",
        executions=[
            _execution("passed", 0.5),
        ],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    baseline = mocker.patch.object(
        classifier,
        "_measure_own_baseline",
    )

    blocked = mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={
            "test_example": {
                "outcome": "passed",
            }
        },
    )

    classifier.flaky_tests_post(run)

    baseline.assert_not_called()

    blocked.assert_called_once_with(
        ["test_example"],
        pytest.approx(1.5),
    )

    assert len(test.flakefighter_results) == 1
    assert (
        test.flakefighter_results[0].name
        == "NetworkClassifier"
    )
    assert test.flakefighter_results[0].flaky is False

def test_existing_failed_execution_is_inconclusive(mocker):
    """Test existing failed baseline."""
    test = Test(
        name="test_example",
        executions=[
            _execution("failed", 0.5),
        ],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    baseline = mocker.patch.object(
        classifier,
        "_measure_own_baseline",
    )

    blocked = mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
    )

    classifier.flaky_tests_post(run)

    baseline.assert_not_called()
    blocked.assert_not_called()

    assert test.flakefighter_results == []

def test_missing_execution_stores_passing_baseline(mocker):
    """Test storing a new passing baseline execution."""
    test = Test(
        name="test_example",
        executions=[],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    baseline_report = {
        "nodeid": "test_example",
        "outcome": "passed",
        "setup": {"duration": 0.1},
        "call": {"duration": 0.3},
        "teardown": {"duration": 0.1},
    }

    mocker.patch.object(
        classifier,
        "_measure_own_baseline",
        return_value={
            "test_example": {
                "outcome": "passed",
                "duration": 0.5,
                "report": baseline_report,
            }
        },
    )

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={
            "test_example": {
                "outcome": "passed",
            }
        },
    )

    classifier.flaky_tests_post(run)

    assert len(test.executions) == 1

    execution = test.executions[0]

    assert execution.outcome == "passed"
    assert json.loads(execution.report) == baseline_report

    assert len(test.flakefighter_results) == 1
    assert test.flakefighter_results[0].flaky is False

def test_missing_execution_stores_failed_baseline(mocker):
    """Test storing a failed baseline execution."""
    test = Test(
        name="test_example",
        executions=[],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    baseline_report = {
        "nodeid": "test_example",
        "outcome": "failed",
    }

    mocker.patch.object(
        classifier,
        "_measure_own_baseline",
        return_value={
            "test_example": {
                "outcome": "failed",
                "duration": None,
                "report": baseline_report,
            }
        },
    )

    blocked = mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
    )

    classifier.flaky_tests_post(run)

    assert len(test.executions) == 1

    execution = test.executions[0]

    assert execution.outcome == "failed"
    assert json.loads(execution.report) == baseline_report

    blocked.assert_not_called()

    assert test.flakefighter_results == []

def test_socket_blocked_is_flaky(mocker):
    """Test network-sensitive classification."""
    test = Test(
        name="test_example",
        executions=[
            _execution("passed", 0.5),
        ],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={
            "test_example": {
                "outcome": "failed",
                "call": {
                    "outcome": "failed",
                    "longrepr": (
                        "pytest_socket.SocketBlockedError: "
                        "socket disabled"
                    ),
                },
            }
        },
    )

    classifier.flaky_tests_post(run)

    assert len(test.flakefighter_results) == 1
    assert (
        test.flakefighter_results[0].name
        == "NetworkClassifier"
    )
    assert test.flakefighter_results[0].flaky is True

def test_unrelated_failure_is_genuine(mocker):
    """Test unrelated blocked-run failure."""
    test = Test(
        name="test_example",
        executions=[
            _execution("passed", 0.5),
        ],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={
            "test_example": {
                "outcome": "failed",
                "call": {
                    "outcome": "failed",
                    "longrepr": "AssertionError",
                },
            }
        },
    )

    classifier.flaky_tests_post(run)

    assert len(test.flakefighter_results) == 1
    assert test.flakefighter_results[0].flaky is False

def test_timeout_is_inconclusive(mocker):
    """Test blocked-run timeout."""
    test = Test(
        name="test_example",
        executions=[
            _execution("passed", 0.5),
        ],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={
            "test_example": {
                "outcome": "failed",
                "call": {
                    "outcome": "failed",
                    "longrepr": (
                        "Failed: Timeout >1.5s"
                    ),
                },
            }
        },
    )

    classifier.flaky_tests_post(run)

    assert test.flakefighter_results == []

def test_missing_blocked_report_is_inconclusive(mocker):
    """Test missing blocked report."""
    test = Test(
        name="test_example",
        executions=[
            _execution("passed", 0.5),
        ],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={},
    )

    classifier.flaky_tests_post(run)

    assert test.flakefighter_results == []

def test_blocked_run_failure_is_inconclusive(mocker):
    """Test failed blocked batch."""
    test = Test(
        name="test_example",
        executions=[
            _execution("passed", 0.5),
        ],
    )

    run = Run(tests=[test])

    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value=None,
    )

    classifier.flaky_tests_post(run)

    assert test.flakefighter_results == []

def test_no_tests(mocker):
    """Test empty run."""
    run = Run(tests=[])

    classifier = NetworkClassifier()

    blocked = mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
    )

    classifier.flaky_tests_post(run)

    blocked.assert_not_called()