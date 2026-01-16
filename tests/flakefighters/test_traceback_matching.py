"""
This module tests the traceback matching flakefighters.
"""

import os
from copy import deepcopy

import pytest

from pytest_flakefighters.database_management import (
    Database,
    FlakefighterResult,
    Run,
    Test,
    TestException,
    TestExecution,
    TracebackEntry,
)
from pytest_flakefighters.flakefighters.traceback_matching import (
    CosineSimilarity,
    TracebackMatching,
)


@pytest.fixture(scope="function", name="test_execution")
def _test_execution(flaky_reruns_repo):
    return TestExecution(
        outcome="failed",
        exception=TestException(
            name="AssertionError",
            traceback=[
                TracebackEntry(
                    id=23,
                    exception_id=1,
                    path=os.path.join(
                        flaky_reruns_repo.working_dir,
                        "venv",
                        "lib",
                        "python3.11",
                        "site-packages",
                        "_pytest",
                        "python.py",
                    ),
                    lineno=165,
                    colno=13,
                    statement="    result = testfunction(**testargs)",
                    source="""
@hookimpl(trylast=True)
def pytest_pyfunc_call(pyfuncitem: Function) -> object | None:
    testfunction = pyfuncitem.obj
    if is_async_function(testfunction):
        async_fail(pyfuncitem.nodeid)
        funcargs = pyfuncitem.funcargs
        testargs = {arg: funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
        result = testfunction(**testargs)""",
                ),
                TracebackEntry(
                    path=os.path.join(
                        flaky_reruns_repo.working_dir,
                        "flaky_reruns.py",
                    ),
                    lineno=21,
                    colno=8,
                    statement="        assert result",
                    source="""
        def test_create_or_delete(self):
            flaky = FlakyReruns("test.txt")
            result = flaky.create_or_delete()
            assert result
            """,
                ),
            ],
        ),
    )


@pytest.mark.parametrize("matcher", [TracebackMatching, CosineSimilarity])
def test_from_config_params(flaky_reruns_repo, matcher):
    """
    Test that from_config generates the same result as a direct call
    """
    db = Database(f"sqlite:///{os.path.join(flaky_reruns_repo.working_dir, 'flakefighters.db')}")

    from_config = matcher.from_config({"run_live": False, "root": flaky_reruns_repo.working_dir, "database": db})
    init = matcher(run_live=False, previous_runs=db.previous_runs, root=flaky_reruns_repo.working_dir)
    assert from_config.run_live == init.run_live
    assert from_config.root == init.root
    assert from_config.previous_runs == init.previous_runs
    assert from_config.params() == init.params()


@pytest.mark.parametrize("matcher", [TracebackMatching, CosineSimilarity])
def test_no_exception(test_execution, matcher):
    """
    Test that the live classification classifies a flaky test.
    """
    previous_test_execution = deepcopy(test_execution)
    previous_test_execution.flakefighter_results = [FlakefighterResult(name="DeFlaker", flaky=True)]
    previous_runs = [Run(tests=[Test(executions=[previous_test_execution])])]

    matcher = matcher(run_live=True, previous_runs=previous_runs)
    assert test_execution.flakefighter_results == []
    test_execution.exception = None
    matcher.flaky_test_live(test_execution)
    assert test_execution.flakefighter_results == [FlakefighterResult(name=matcher.__class__.__name__, flaky=False)]


@pytest.mark.parametrize("matcher", [TracebackMatching, CosineSimilarity])
@pytest.mark.parametrize("flaky", [True, False])
def test_flaky_test_live(test_execution, matcher, flaky):
    """
    Test that the live classification classifies a flaky test.
    """
    previous_test_execution = deepcopy(test_execution)
    previous_test_execution.flakefighter_results = [FlakefighterResult(name="DeFlaker", flaky=flaky)]
    previous_runs = [Run(tests=[Test(executions=[previous_test_execution])])]

    matcher = matcher(run_live=True, previous_runs=previous_runs)
    assert test_execution.flakefighter_results == []
    matcher.flaky_test_live(test_execution)
    assert test_execution.flakefighter_results == [FlakefighterResult(name=matcher.__class__.__name__, flaky=flaky)]


@pytest.mark.parametrize("matcher", [TracebackMatching, CosineSimilarity])
@pytest.mark.parametrize("flaky", [True, False])
def test_flaky_tests_post(test_execution, matcher, flaky):
    """
    Test that the post-hoc classification classifies a flaky test.
    """
    previous_test_execution = deepcopy(test_execution)
    previous_test_execution.flakefighter_results = [FlakefighterResult(name="DeFlaker", flaky=flaky)]
    previous_runs = [Run(tests=[Test(executions=[previous_test_execution])])]

    current_run = Run(tests=[Test(executions=[test_execution])])

    matcher = matcher(run_live=False, previous_runs=previous_runs)
    test_execution = current_run.tests[0].executions[0]
    assert test_execution.flakefighter_results == []
    matcher.flaky_tests_post(current_run)
    assert test_execution.flakefighter_results == [FlakefighterResult(name=matcher.__class__.__name__, flaky=flaky)]
