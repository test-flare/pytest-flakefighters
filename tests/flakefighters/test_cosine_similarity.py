"""
This module tests the CosineSimilarity flakefighter.
"""

import os
from copy import deepcopy

import pytest

from pytest_flakefighters.database_management import (
    Database,
    FlakefighterResult,
    Run,
    Test,
)
from pytest_flakefighters.flakefighters.traceback_matching import CosineSimilarity


def test_from_config_params(flaky_reruns_repo):
    """
    Test that from_config generates the same result as a direct call
    """
    db = Database(f"sqlite:///{os.path.join(flaky_reruns_repo.working_dir, 'flakefighters.db')}")

    from_config = CosineSimilarity.from_config(
        {"run_live": True, "root": flaky_reruns_repo.working_dir, "database": db}
    )
    init = CosineSimilarity(run_live=True, previous_runs=db.previous_runs, root=flaky_reruns_repo.working_dir)
    assert from_config.run_live == init.run_live
    assert from_config.root == init.root
    assert from_config.previous_runs == init.previous_runs
    assert from_config.params() == init.params()


def test_no_exception(test_execution):
    """
    Test that the live classification classifies a flaky test.
    """
    previous_test_execution = deepcopy(test_execution)
    previous_test_execution.flakefighter_results = [FlakefighterResult(name="DeFlaker", flaky=True)]
    previous_runs = [Run(tests=[Test(executions=[previous_test_execution])])]

    matcher = CosineSimilarity(run_live=True, previous_runs=previous_runs)
    assert test_execution.flakefighter_results == []
    test_execution.exception = None
    matcher.flaky_test_live(test_execution)
    assert test_execution.flakefighter_results == [FlakefighterResult(name="CosineSimilarity", flaky=False)]


@pytest.mark.parametrize("flaky", [True, False])
def test_flaky_test_live(test_execution, flaky):
    """
    Test that the live classification classifies a flaky test.
    """
    previous_test_execution = deepcopy(test_execution)
    previous_test_execution.flakefighter_results = [FlakefighterResult(name="DeFlaker", flaky=flaky)]
    previous_runs = [Run(tests=[Test(executions=[previous_test_execution])])]

    matcher = CosineSimilarity(run_live=True, previous_runs=previous_runs)
    assert test_execution.flakefighter_results == []
    matcher.flaky_test_live(test_execution)
    assert test_execution.flakefighter_results == [FlakefighterResult(name="CosineSimilarity", flaky=flaky)]


@pytest.mark.parametrize("flaky", [True, False])
def test_flaky_tests_post(test_execution, flaky):
    """
    Test that the post-hoc classification classifies a flaky test.
    """
    previous_test_execution = deepcopy(test_execution)
    previous_test_execution.flakefighter_results = [FlakefighterResult(name="DeFlaker", flaky=flaky)]
    previous_runs = [Run(tests=[Test(executions=[previous_test_execution])])]

    current_run = Run(tests=[Test(executions=[test_execution])])

    matcher = CosineSimilarity(run_live=False, previous_runs=previous_runs)
    test_execution = current_run.tests[0].executions[0]
    assert test_execution.flakefighter_results == []
    matcher.flaky_tests_post(current_run)
    assert test_execution.flakefighter_results == [FlakefighterResult(name="CosineSimilarity", flaky=flaky)]
