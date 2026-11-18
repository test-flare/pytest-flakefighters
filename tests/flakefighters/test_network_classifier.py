"""Unit tests for the NetworkClassifier FlakeFighter."""

# pylint: disable=protected-access

import json
from datetime import datetime, timedelta

import pytest

from pytest_flakefighters.database_management import Run, Test, TestExecution
from pytest_flakefighters.flakefighters.network_classifier import NetworkClassifier


def _execution(outcome, duration=None):
    """Create a real TestExecution for unit tests."""
    if duration is None:
        return TestExecution(outcome=outcome, start_time=None, end_time=None)

    start = datetime(2026, 1, 1, 12, 0, 0)

    return TestExecution(
        outcome=outcome, start_time=start, end_time=start + timedelta(seconds=duration)
    )


def _test_with_execution(outcome="passed", duration=0.5, name="test_example"):
    """Create a Test with one execution."""
    return Test(name=name, executions=[_execution(outcome, duration)])


def _passed_report(nodeid="test_example"):
    """Return a simple passing pytest report."""
    return {"nodeid": nodeid, "outcome": "passed"}


def _failed_report(message, nodeid="test_example"):
    """Return a simple failed pytest report."""
    return {
        "nodeid": nodeid,
        "outcome": "failed",
        "call": {"outcome": "failed", "longrepr": message},
    }


def _mock_pytest_report(mocker, classifier, report):
    """Mock a pytest subprocess and write the supplied JSON report."""

    def fake_run(command, cwd, env):
        del cwd, env

        report_arg = next(arg for arg in command if arg.startswith("--json-report-file="))
        report_path = report_arg.split("=", 1)[1]

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(report, file)

        return True

    return mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_run)


def _mock_invalid_json_report(mocker, classifier):
    """Mock a pytest subprocess that writes invalid JSON."""

    def fake_run(command, cwd, env):
        del cwd, env

        report_arg = next(arg for arg in command if arg.startswith("--json-report-file="))
        report_path = report_arg.split("=", 1)[1]

        with open(report_path, "w", encoding="utf-8") as file:
            file.write("not valid json")

        return True

    return mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_run)


def test_from_config_params():
    """Test that configuration values are applied correctly."""
    config = {"root": ".", "extra_pytest_args": ["-vv"]}

    from_config = NetworkClassifier.from_config(config)
    direct = NetworkClassifier(root=".", extra_pytest_args=["-vv"])

    assert from_config.params() == direct.params()


def test_flaky_test_live_not_supported():
    """Test that live classification is not supported."""
    classifier = NetworkClassifier()

    with pytest.raises(NotImplementedError, match="only supports postprocessing"):
        classifier.flaky_test_live(None)


def test_longest_passed_duration():
    """Test that the longest successful execution duration is returned."""
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
    """Test that no duration is returned when no execution passed."""
    test = Test(
        name="test_example", executions=[_execution("failed", 0.5), _execution("failed", 1.0)]
    )

    classifier = NetworkClassifier()

    assert classifier._longest_passed_duration(test) is None


def test_longest_passed_duration_missing_times():
    """Test that passing executions with missing timing data are ignored."""
    test = _test_with_execution(outcome="passed", duration=None)

    classifier = NetworkClassifier()

    assert classifier._longest_passed_duration(test) is None


def test_longest_passed_duration_missing_end_time():
    """Test that a passing execution with no end time is ignored."""
    test = Test(
        name="test_example",
        executions=[
            TestExecution(
                outcome="passed", start_time=datetime(2026, 1, 1, 12, 0, 0), end_time=None
            )
        ],
    )

    classifier = NetworkClassifier()

    assert classifier._longest_passed_duration(test) is None


@pytest.mark.parametrize(
    ("durations", "expected"), [([0.2, 0.8, 0.5], 2.4), ([0.1, 0.2], 1.0), ([], 1.0)]
)
def test_compute_timeout(durations, expected):
    """Test timeout calculation from successful execution durations."""
    classifier = NetworkClassifier()

    assert classifier._compute_timeout(durations) == pytest.approx(expected)


def test_subprocess_env(monkeypatch):
    """Test that conflicting environment variables are removed."""
    monkeypatch.setenv("PYTEST_ADDOPTS", "--some-option")
    monkeypatch.setenv("COVERAGE_FILE", ".coverage")
    monkeypatch.setenv("KEEP_ME", "yes")

    classifier = NetworkClassifier()

    env = classifier._subprocess_env()

    assert "PYTEST_ADDOPTS" not in env
    assert "COVERAGE_FILE" not in env
    assert env["KEEP_ME"] == "yes"


def test_run_pytest_subprocess_success(mocker):
    """Test successful child pytest process execution."""
    subprocess_run = mocker.patch(
        "pytest_flakefighters.flakefighters.network_classifier.subprocess.run"
    )

    classifier = NetworkClassifier()

    result = classifier._run_pytest_subprocess(["python", "-m", "pytest"], cwd=".", env={})

    assert result is True
    subprocess_run.assert_called_once()


def test_run_pytest_subprocess_oserror(mocker):
    """Test subprocess launch failure handling."""
    mocker.patch(
        "pytest_flakefighters.flakefighters.network_classifier.subprocess.run", side_effect=OSError
    )

    classifier = NetworkClassifier()

    result = classifier._run_pytest_subprocess(["python", "-m", "pytest"], cwd=".", env={})

    assert result is False


def test_report_socket_blocked():
    """Test detection of SocketBlockedError in a report."""
    classifier = NetworkClassifier()

    report = _failed_report("pytest_socket.SocketBlockedError: A test tried to use socket.socket")

    assert classifier._report_confirms_socket_blocked(report) is True


def test_report_socket_connect_blocked():
    """Test detection of SocketConnectBlockedError in a report."""
    classifier = NetworkClassifier()

    report = {
        "outcome": "failed",
        "call": {
            "outcome": "failed",
            "crash": {
                "message": (
                    "pytest_socket.SocketConnectBlockedError: " "A test tried to use socket.connect"
                )
            },
        },
    }

    assert classifier._report_confirms_socket_blocked(report) is True


def test_report_unrelated_failure():
    """Test that unrelated failures are not treated as socket blocking."""
    classifier = NetworkClassifier()

    report = _failed_report("AssertionError: expected 1 but got 2")

    assert classifier._report_confirms_socket_blocked(report) is False


def test_report_timeout():
    """Test detection of pytest-timeout failures."""
    classifier = NetworkClassifier()

    report = _failed_report("Failed: Timeout >2.0s")

    assert classifier._report_confirms_timeout(report) is True


@pytest.mark.parametrize(
    "report",
    [
        {"outcome": "failed"},
        {"outcome": "error"},
        {"outcome": "passed", "setup": {"outcome": "failed"}},
        {"outcome": "passed", "call": {"outcome": "failed"}},
        {"outcome": "passed", "teardown": {"outcome": "error"}},
    ],
)
def test_report_failed(report):
    """Test detection of failed or errored pytest reports."""
    classifier = NetworkClassifier()

    assert classifier._report_failed(report) is True


def test_report_passed():
    """Test that a passing report is not treated as failed."""
    classifier = NetworkClassifier()

    report = {
        "outcome": "passed",
        "setup": {"outcome": "passed"},
        "call": {"outcome": "passed"},
        "teardown": {"outcome": "passed"},
    }

    assert classifier._report_failed(report) is False


def test_run_with_disabled_socket_parses_report(mocker):
    """Test blocked-network command construction and report parsing."""
    classifier = NetworkClassifier()
    captured_command = {}

    def fake_run(command, cwd, env):
        del cwd, env

        captured_command["command"] = command

        report_arg = next(arg for arg in command if arg.startswith("--json-report-file="))
        report_path = report_arg.split("=", 1)[1]

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "tests": [
                        _failed_report(
                            "pytest_socket.SocketBlockedError: socket disabled",
                            nodeid="test_a.py::test_a",
                        )
                    ]
                },
                file,
            )

        return True

    mocker.patch.object(classifier, "_run_pytest_subprocess", side_effect=fake_run)

    reports = classifier._run_with_disabled_socket(["test_a.py::test_a"], 2.4)

    command = captured_command["command"]

    assert "--disable-socket" in command
    assert "--allow-unix-socket" in command
    assert "--allow-hosts=localhost,127.0.0.1,::1" in command
    assert "--timeout=2.4" in command
    assert "-p" in command
    assert "no:flakefighters" in command
    assert reports["test_a.py::test_a"]["outcome"] == "failed"


def test_run_with_disabled_socket_subprocess_failure(mocker):
    """Test blocked-network handling when the subprocess fails."""
    classifier = NetworkClassifier()

    mocker.patch.object(classifier, "_run_pytest_subprocess", return_value=False)

    result = classifier._run_with_disabled_socket(["test_a.py::test_a"], 2.0)

    assert result is None


def test_run_with_disabled_socket_no_nodeids(mocker):
    """Test that no blocked subprocess is run without node IDs."""
    classifier = NetworkClassifier()

    subprocess_run = mocker.patch.object(classifier, "_run_pytest_subprocess")

    result = classifier._run_with_disabled_socket([], 1.0)

    assert not result
    subprocess_run.assert_not_called()


def test_run_with_disabled_socket_invalid_json(mocker):
    """Test blocked-network handling when the JSON report is invalid."""
    classifier = NetworkClassifier()

    _mock_invalid_json_report(mocker, classifier)

    result = classifier._run_with_disabled_socket(["test_a.py::test_a"], 1.0)

    assert result is None


def test_run_with_disabled_socket_tests_not_list(mocker):
    """Test blocked-network handling when the tests field is malformed."""
    classifier = NetworkClassifier()

    _mock_pytest_report(mocker, classifier, {"tests": "invalid"})

    result = classifier._run_with_disabled_socket(["test_a.py::test_a"], 1.0)

    assert result is None


def test_existing_pass_is_eligible(mocker):
    """Test that an existing passing execution is eligible."""
    test = _test_with_execution()
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    blocked = mocker.patch.object(
        classifier, "_run_with_disabled_socket", return_value={"test_example": _passed_report()}
    )

    classifier.flaky_tests_post(run)

    blocked.assert_called_once_with(["test_example"], pytest.approx(1.5))

    assert len(test.flakefighter_results) == 1
    assert test.flakefighter_results[0].name == "NetworkClassifier"
    assert test.flakefighter_results[0].flaky is False


def test_existing_pass_without_timing_is_still_eligible(mocker):
    """Test that a passing execution without timing stays eligible."""
    test = _test_with_execution(duration=None)
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    blocked = mocker.patch.object(
        classifier, "_run_with_disabled_socket", return_value={"test_example": _passed_report()}
    )

    classifier.flaky_tests_post(run)

    blocked.assert_called_once_with(["test_example"], pytest.approx(1.0))


def test_existing_failed_execution_is_inconclusive(mocker):
    """Test that a failed-only existing baseline is inconclusive."""
    test = _test_with_execution(outcome="failed")
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    blocked = mocker.patch.object(classifier, "_run_with_disabled_socket")

    classifier.flaky_tests_post(run)

    blocked.assert_not_called()
    assert not test.flakefighter_results


def test_missing_execution_is_inconclusive(mocker):
    """Test that a test with no current execution is not classified."""
    test = Test(name="test_example", executions=[])
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    blocked = mocker.patch.object(classifier, "_run_with_disabled_socket")

    classifier.flaky_tests_post(run)

    blocked.assert_not_called()
    assert not test.flakefighter_results


def test_socket_blocked_is_flaky(mocker):
    """Test classification of a socket-blocked failure as network-sensitive."""
    test = _test_with_execution()
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={
            "test_example": _failed_report("pytest_socket.SocketBlockedError: socket disabled")
        },
    )

    classifier.flaky_tests_post(run)

    assert len(test.flakefighter_results) == 1
    assert test.flakefighter_results[0].name == "NetworkClassifier"
    assert test.flakefighter_results[0].flaky is True


def test_unrelated_failure_is_genuine(mocker):
    """Test that an unrelated blocked failure is not network-sensitive."""
    test = _test_with_execution()
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={"test_example": _failed_report("AssertionError")},
    )

    classifier.flaky_tests_post(run)

    assert len(test.flakefighter_results) == 1
    assert test.flakefighter_results[0].flaky is False


def test_timeout_is_inconclusive(mocker):
    """Test that a blocked-run timeout leaves the result inconclusive."""
    test = _test_with_execution()
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    mocker.patch.object(
        classifier,
        "_run_with_disabled_socket",
        return_value={"test_example": _failed_report("Failed: Timeout >1.5s")},
    )

    classifier.flaky_tests_post(run)

    assert not test.flakefighter_results


def test_missing_blocked_report_is_inconclusive(mocker):
    """Test that a missing blocked report leaves the result inconclusive."""
    test = _test_with_execution()
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    mocker.patch.object(classifier, "_run_with_disabled_socket", return_value={})

    classifier.flaky_tests_post(run)

    assert not test.flakefighter_results


def test_blocked_run_failure_is_inconclusive(mocker):
    """Test that an unusable blocked run leaves the result inconclusive."""
    test = _test_with_execution()
    run = Run(tests=[test])
    classifier = NetworkClassifier()

    mocker.patch.object(classifier, "_run_with_disabled_socket", return_value=None)

    classifier.flaky_tests_post(run)

    assert not test.flakefighter_results


def test_no_tests(mocker):
    """Test that an empty run performs no network classification."""
    run = Run(tests=[])
    classifier = NetworkClassifier()

    blocked = mocker.patch.object(classifier, "_run_with_disabled_socket")

    classifier.flaky_tests_post(run)

    blocked.assert_not_called()
