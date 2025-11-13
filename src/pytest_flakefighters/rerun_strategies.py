"""
This module implements the various supported test rerun strategies.
"""

from abc import ABC, abstractmethod

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from pytest_flakefighters.database_management import Database, Test


class RerunStrategy(ABC):
    """
    Abstract base class for test rerun strategies.
    """

    def __init__(self, max_reruns: int):
        self.max_reruns = max_reruns

    @abstractmethod
    def rerun(self, report: pytest.TestReport) -> bool:
        """
        Decide whether to rerun a test case.
        :return: Boolean true to rerun, False otherwise.
        """

    @classmethod
    @abstractmethod
    def help(cls) -> str:
        """
        Return the help string for config options.
        """


class All(RerunStrategy):
    """
    Rerun all tests, regardless of outcome.
    """

    def rerun(self, report: pytest.TestReport) -> bool:
        """
        Trivially rerun all tests, regardless of outcome.
        :return: Boolean true to rerun, False otherwise.
        """
        return True

    @classmethod
    def help(cls):
        return "Trivially rerun all tests, regardless of outcome."


class FlakyFailure(RerunStrategy):
    """
    Strategy to rerun failed tests marked as flaky.
    """

    def rerun(self, report: pytest.TestReport) -> bool:
        """
        :return: Boolean true if a test fails and has been marked as flaky by live FlakeFighters.
        """
        return report.flaky and not report.passed

    @classmethod
    def help(cls):
        return "Rerun failing tests that have been merked as flaky by live FlakeFighters."


class PreviouslyFlaky(FlakyFailure):
    """
    Rerun failed tests marked as flaky and tests previously marked as flaky.
    """

    def __init__(self, reruns: int, database: Database):
        super().__init__(reruns)
        with Session(database.engine) as session:
            tests = session.scalars(select(Test)).all()
            self.previously_flaky = list(filter(lambda t: t.flaky, tests))

    def rerun(self, report: pytest.TestReport) -> bool:
        """
        :return: Boolean true if a test is a flaky failure or has previously been marked as flaky and has the same name
        as the current test.
        """
        return super().rerun(report) or any(test.name == report.nodeid for test in self.previously_flaky)

    @classmethod
    def help(cls):
        return "Rerun failing tests marked as flaky, and tests that have previously been marked as flaky."
