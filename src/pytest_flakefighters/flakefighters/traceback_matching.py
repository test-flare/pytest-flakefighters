"""
This module implements three FlakeFighters based on failure de-duplication from Alshammari et. al.
[https://arxiv.org/pdf/2401.15788].
"""

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    TestExecution,
)
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter


class TracebackMatching(FlakeFighter):
    """
    Simple Text-Based Matching classifier from Section II.A of [Alshammari et. al.].
    We implement text-based matching on the failure logs for each test. Each failure log is represented by its failure
    exception and stacktrace.
    """

    def __init__(self, run_live: bool, previous_runs: list[Run], root: str = "."):
        super().__init__(run_live)
        self.root = root
        self.previous_runs = previous_runs

    def params(self):
        return {"root": self.root}

    def flaky_test_live(self, execution: TestExecution):
        for entry in execution.exception.traceback:
            print(entry.path)

    def flaky_tests_post(self, run: Run) -> list[bool | None]:
        """
        Classify failing tests as flaky if any of their executions are flaky.
        :param run: Run object representing the pytest run, with tests accessible through run.tests.
        """
        for test in run.tests:
            test.flakefighter_results.append(
                FlakefighterResult(
                    name=self.__class__.__name__,
                    flaky=any(self.flaky_test_live(execution) for execution in test.executions),
                )
            )
