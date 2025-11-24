import datetime
import os

import pytest

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    Test,
    TestException,
    TestExecution,
    TracebackEntry,
)
from pytest_flakefighters.flakefighters.traceback_matching import (
    TracebackMatching,
)


def test_flaky_test_live(flaky_reruns_repo):
    test_execution = TestExecution(
        id=1,
        test_id=1,
        outcome="failed",
        exception=TestException(
            id=1,
            execution_id=1,
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
                    id=24,
                    exception_id=1,
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
        flakefighter_results=[FlakefighterResult(name="DeFlaker", flaky=True)],
    )
    previous_runs = [Run(tests=[Test(executions=[test_execution])])]

    matcher = TracebackMatching(run_live=True, previous_runs=previous_runs)
    matcher.flaky_test_live(test_execution)
    assert test_execution.flakefighter_results == [FlakefighterResult(name="TracebackMatching", flaky=True)]
