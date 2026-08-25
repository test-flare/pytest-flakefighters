"""
Unit tests for the OrderDependency FlakeFighter.
"""

# pylint: disable=protected-access

import json
import os
from types import SimpleNamespace
import pytest

from pytest_flakefighters.flakefighters.order_dependency import OrderDependency

def make_test(name, outcomes):
    """Create a simple test with current-run execution outcomes."""
    return SimpleNamespace(
        name=name,
        executions=[SimpleNamespace(outcome=outcome) for outcome in outcomes],
        flakefighter_results=[],
        order_dependency_executions=[],
    )

def make_database(previous_runs=None):
    """Create a simple database object with optional previous runs."""
    return SimpleNamespace(previous_runs=previous_runs or [])

def test_configuration():
    """OrderDependency should use its configured mode and number of runs."""

    database = make_database()

    fighter = OrderDependency.from_config(
        {"database": database, "mode": "reverse", "order_runs": 3}
    )

    assert fighter.database is database
    assert fighter.run_live is False
    assert fighter.params() == {"mode": "reverse", "order_runs": 3}

def test_default_configuration():
    """Random mode and one perturbation run should be the defaults."""

    fighter = OrderDependency.from_config({"database": make_database()})

    assert fighter.params() == {"mode": "random", "order_runs": 1}

def test_invalid_mode():
    """Only random and reverse modes should be accepted."""

    with pytest.raises(ValueError):
        OrderDependency(database=make_database(), mode="invalid")

def test_order_runs_cannot_be_less_than_one():
    """Random mode should always perform at least one perturbation."""

    fighter = OrderDependency(database=make_database(), order_runs=0)

    assert fighter.order_runs == 1

def test_live_classification_is_not_used():
    """OrderDependency is a post-processing FlakeFighter."""

    fighter = OrderDependency(database=make_database())

    assert fighter.flaky_test_live(None) is None

def test_collect_current_baseline():
    """
    The current FlakeFighters run should provide the baseline.

    Skipped outcomes are ignored and the latest usable execution is used.
    """

    run = SimpleNamespace(
        tests=[
            make_test("test_pass", ["passed"]),
            make_test("test_fail", ["failed"]),
            make_test("test_rerun", ["failed", "passed"]),
            make_test("test_skip", ["skipped"]),
        ]
    )

    baseline = OrderDependency._collect_baseline(run)

    assert baseline == {"test_pass": "passed", "test_fail": "failed", "test_rerun": "passed"}

def test_reverse_order():
    """Reverse mode should execute the tests in reverse order."""

    fighter = OrderDependency(database=make_database(), mode="reverse")

    order = fighter._make_order(["test_one", "test_two", "test_three"], seed=None)

    assert order == ["test_three", "test_two", "test_one"]

def test_random_order_uses_seed():
    """The same random seed should reproduce the same shuffled order."""

    fighter = OrderDependency(database=make_database(), mode="random")

    tests = ["test_one", "test_two", "test_three"]

    first_order = fighter._make_order(tests, 5)
    second_order = fighter._make_order(tests, 5)

    assert first_order == second_order

def test_random_seed_starts_at_zero():
    """The first random perturbation should use seed 0."""

    fighter = OrderDependency(database=make_database())

    assert fighter._next_seed() == 0

def test_random_seed_continues_from_history():
    """New random perturbations should continue after historical seeds."""

    previous_run = SimpleNamespace(
        order_dependency_executions=[
            SimpleNamespace(mode="random", seed=0),
            SimpleNamespace(mode="random", seed=1),
            SimpleNamespace(mode="reverse", seed=None),
        ]
    )

    fighter = OrderDependency(database=make_database([previous_run]))

    assert fighter._next_seed() == 2

def test_extract_pass_fail_outcomes():
    """Only passed and failed outcomes should be used as evidence."""

    report = {
        "tests": [
            {"nodeid": "test_pass", "outcome": "passed"},
            {"nodeid": "test_fail", "outcome": "failed"},
            {"nodeid": "test_skip", "outcome": "skipped"},
            {"outcome": "passed"},
        ]
    }

    outcomes = OrderDependency._extract_outcomes(report)

    assert outcomes == {"test_pass": "passed", "test_fail": "failed"}

def test_load_historical_random_outcomes():
    """Only previous random PASS/FAIL executions should be reused."""

    previous_test = SimpleNamespace(name="test_example")

    previous_run = SimpleNamespace(
        order_dependency_executions=[
            SimpleNamespace(mode="random", outcome="passed", test=previous_test),
            SimpleNamespace(mode="random", outcome="failed", test=previous_test),
            SimpleNamespace(mode="reverse", outcome="passed", test=previous_test),
            SimpleNamespace(mode="random", outcome="skipped", test=previous_test),
        ]
    )

    fighter = OrderDependency(database=make_database([previous_run]))

    outcomes = fighter._load_historical_outcomes()

    assert outcomes["test_example"] == {"passed", "failed"}

def test_store_order_execution():
    """Perturbation outcomes should be attached to their run and test."""

    test_one = make_test("test_one", ["passed"])
    test_two = make_test("test_two", ["passed"])

    run = SimpleNamespace(tests=[test_one, test_two], order_dependency_executions=[])

    OrderDependency._store_order_execution(
        run=run,
        mode="random",
        seed=2,
        ordered_nodeids=["test_one", "unknown_test", "test_two"],
        outcomes={"test_one": "passed", "unknown_test": "passed", "test_two": "skipped"},
    )

    assert len(run.order_dependency_executions) == 1

    execution = run.order_dependency_executions[0]

    assert execution.mode == "random"
    assert execution.seed == 2
    assert execution.position == 0
    assert execution.outcome == "passed"

    assert test_one.order_dependency_executions == [execution]
    assert test_two.order_dependency_executions == []

def test_classification():
    """
    PASS + FAIL means order dependent.
    """

    flaky_test = make_test("test_flaky", ["passed"])
    genuine_test = make_test("test_genuine", ["passed"])
    ignored_test = make_test("test_without_evidence", ["passed"])

    run = SimpleNamespace(tests=[flaky_test, genuine_test, ignored_test])

    OrderDependency._classify(run, {"test_flaky": {"passed", "failed"}, "test_genuine": {"passed"}})

    assert flaky_test.flakefighter_results[0].flaky is True
    assert genuine_test.flakefighter_results[0].flaky is False
    assert ignored_test.flakefighter_results == []

def test_reverse_flow(mocker):
    """
    Reverse mode should compare the current baseline
    with one reversed execution.
    """

    fighter = OrderDependency(database=make_database(), mode="reverse")

    test_one = make_test("test_one", ["passed"])
    test_two = make_test("test_two", ["failed"])

    run = SimpleNamespace(
        tests=[test_one, test_two], root="/project", order_dependency_executions=[]
    )

    run_ordered_tests = mocker.patch.object(
        fighter,
        "_run_ordered_tests",
        return_value={
            "tests": [
                {"nodeid": "test_two", "outcome": "passed"},
                {"nodeid": "test_one", "outcome": "passed"},
            ]
        },
    )

    mocker.patch.object(fighter, "_store_order_execution")

    fighter.flaky_tests_post(run)

    # test_two changed from FAIL to PASS.
    assert test_two.flakefighter_results[0].flaky is True

    # test_one remained PASS.
    assert test_one.flakefighter_results[0].flaky is False

    run_ordered_tests.assert_called_once_with(
        ordered_nodeids=["test_two", "test_one"], cwd="/project"
    )

def test_random_flow_uses_history_and_fresh_run(mocker):
    """
    Random mode should combine the current baseline,
    historical random evidence, and a fresh shuffled run.
    """

    previous_test = SimpleNamespace(name="test_example")

    previous_run = SimpleNamespace(
        order_dependency_executions=[
            SimpleNamespace(mode="random", seed=0, outcome="failed", test=previous_test)
        ]
    )

    fighter = OrderDependency(database=make_database([previous_run]), mode="random", order_runs=1)
    test = make_test("test_example", ["passed"])
    run = SimpleNamespace(tests=[test], root="/project", order_dependency_executions=[])

    mocker.patch.object(
        fighter,
        "_run_ordered_tests",
        return_value={"tests": [{"nodeid": "test_example", "outcome": "passed"}]},
    )

    mocker.patch.object(fighter, "_store_order_execution")

    fighter.flaky_tests_post(run)

    # Current baseline = PASS
    # Historical random execution = FAIL
    # Therefore both outcomes have been observed.
    assert test.flakefighter_results[0].flaky is True

def test_no_baseline_does_nothing(mocker):
    """No perturbation should run when there are no usable baseline outcomes."""

    fighter = OrderDependency(database=make_database())
    run = SimpleNamespace(tests=[make_test("test_skip", ["skipped"])])
    run_ordered_tests = mocker.patch.object(fighter, "_run_ordered_tests")
    fighter.flaky_tests_post(run)

    run_ordered_tests.assert_not_called()

def test_missing_or_empty_perturbation_is_ignored(mocker):
    """A failed or unusable perturbation run should not become evidence."""

    fighter = OrderDependency(database=make_database(), mode="random", order_runs=2)
    test = make_test("test_example", ["passed"])
    run = SimpleNamespace(tests=[test], root="/project", order_dependency_executions=[])

    mocker.patch.object(
        fighter,
        "_run_ordered_tests",
        side_effect=[None, {"tests": [{"nodeid": "test_example", "outcome": "skipped"}]}],
    )

    store_order_execution = mocker.patch.object(fighter, "_store_order_execution")

    fighter.flaky_tests_post(run)

    store_order_execution.assert_not_called()
    assert test.flakefighter_results[0].flaky is False

def test_subprocess_environment(monkeypatch):
    """Pytest and coverage settings should not leak into the perturbation run."""

    monkeypatch.setenv("PYTEST_ADDOPTS", "--something")
    monkeypatch.setenv("COVERAGE_FILE", "coverage.data")
    monkeypatch.setenv("KEEP_ME", "yes")

    env = OrderDependency._subprocess_env()

    assert "PYTEST_ADDOPTS" not in env
    assert "COVERAGE_FILE" not in env
    assert env["KEEP_ME"] == "yes"

def test_run_ordered_tests(mocker, tmp_path):
    """The perturbation subprocess should return its JSON report."""

    fighter = OrderDependency(database=make_database(), extra_pytest_args=["-s"])

    def fake_subprocess(command, **_kwargs):
        report_argument = next(
            argument for argument in command if argument.startswith("--json-report-file=")
        )

        report_path = report_argument.split("=", 1)[1]

        with open(report_path, "w", encoding="utf-8") as report:
            json.dump({"tests": [{"nodeid": "test_example", "outcome": "passed"}]}, report)

    mocker.patch(
        "pytest_flakefighters.flakefighters." "order_dependency.subprocess.run",
        side_effect=fake_subprocess,
    )

    report = fighter._run_ordered_tests(["test_example"], str(tmp_path))

    assert report["tests"][0]["outcome"] == "passed"

def test_invalid_subprocess_report_returns_none(mocker, tmp_path):
    """An unreadable perturbation report should simply be ignored."""

    fighter = OrderDependency(database=make_database())

    mocker.patch("pytest_flakefighters.flakefighters." "order_dependency.subprocess.run")

    assert fighter._run_ordered_tests(["test_example"], str(tmp_path)) is None

def test_missing_subprocess_report_returns_none(mocker, tmp_path):
    """A missing perturbation report should simply be ignored."""

    fighter = OrderDependency(database=make_database())

    def remove_report(command, **_kwargs):
        report_argument = next(
            argument for argument in command if argument.startswith("--json-report-file=")
        )

        report_path = report_argument.split("=", 1)[1]

        if os.path.exists(report_path):
            os.remove(report_path)

    mocker.patch(
        "pytest_flakefighters.flakefighters." "order_dependency.subprocess.run",
        side_effect=remove_report,
    )

    assert fighter._run_ordered_tests(["test_example"], str(tmp_path)) is None
