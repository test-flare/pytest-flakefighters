"""
This module implements three FlakeFighters based on failure de-duplication from Alshammari et. al.
[https://arxiv.org/pdf/2401.15788].
"""

import os

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
        self.root = os.path.abspath(root)
        self.previous_runs = previous_runs

    @classmethod
    def from_config(cls, config: dict):
        """
        Factory method to create a new instance from a pytest configuration.
        """
        return TracebackMatching(
            run_live=config.get("run_live", True),
            previous_runs=config["database"].previous_runs,
            root=config.get("root", "."),
        )

    def params(self):
        """
        Convert the key parameters into a dictionary so that the object can be replicated.
        :return A dictionary of the parameters used to create the object.
        """
        return {"root": self.root}

    def _flaky_execution(self, execution, previous_executions) -> bool:
        """
        Classify an execution as flaky or not.
        :return: Boolean True of the test is classed as flaky and False otherwise.
        """
        if not execution.exception:
            return False
        current_traceback = [
            (os.path.relpath(e.path, self.root), e.lineno, e.colno, e.statement)
            for e in execution.exception.traceback
            if os.path.commonpath([self.root, e.path]) == self.root
        ]
        return any(e == current_traceback for e in previous_executions)

    def all_previous_executions(self) -> list:
        """
        Extract the relevant information from all previous executions and collapse into a single list.
        :return: List containing the relative path, line number, column number, and code statement of all previous
        test executions.
        """
        return [
            [
                (os.path.relpath(elem.path, run.root), elem.lineno, elem.colno, elem.statement)
                for elem in execution.exception.traceback
            ]
            for run in self.previous_runs
            for test in run.tests
            for execution in test.executions
            if any(result.flaky for result in execution.flakefighter_results + test.flakefighter_results)
        ]

    def flaky_test_live(self, execution: TestExecution):
        """
        Classify executions as flaky if they have the same failure logs as a flaky execution.
        :param execution: Test execution to consider.
        """
        execution.flakefighter_results.append(
            FlakefighterResult(
                name=self.__class__.__name__,
                flaky=self._flaky_execution(
                    execution,
                    self.all_previous_executions(),
                ),
            )
        )

    def flaky_tests_post(self, run: Run) -> list[bool | None]:
        """
        Classify failing executions as flaky if any of their executions are flaky.
        :param run: Run object representing the pytest run, with tests accessible through run.tests.
        """
        for test in run.tests:
            for execution in test.executions:
                execution.flakefighter_results.append(
                    FlakefighterResult(
                        name=self.__class__.__name__,
                        flaky=self._flaky_execution(
                            execution,
                            self.all_previous_executions()
                            # Add in all the executions from the current run as long as we're not comparing an
                            # execution to itself
                            + [
                                (os.path.relpath(t.path, self.root), t.lineno, t.colno, t.statement)
                                for test in run.tests
                                for x in test.executions
                                if x.exception
                                for t in x.exception.traceback
                                if t != execution
                            ],
                        ),
                    )
                )
