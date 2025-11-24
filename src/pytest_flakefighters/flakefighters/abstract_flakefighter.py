"""
This module implements the FlakeFighter abstract class to be extended by concrete flakefighter classes.
Each of these is a microservice which takes a failed test and classifies that failure as either genuine or flaky.
This classification can be configured to either run "live" after each test, or as a postprocessing step on the entire
test suite after it completes.
If running live, detectors are run at the end of pytest_runtest_makereport.
If running as a postprocessing step, detectors are run at the start of pytest_sessionfinish.
"""

from abc import ABC, abstractmethod

from pytest_flakefighters.database_management import Run, TestExecution


class FlakeFighter(ABC):  # pylint: disable=R0903
    """
    Abstract base class for a FlakeFighter
    :ivar run_live: Run detection "live" after each test. Otherwise run as a postprocessing step after the test suite.
    """

    def __init__(self, run_live: bool):
        self.run_live = run_live

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict):
        """
        Factory method to create a new instance from a pytest configuration.
        """

    @abstractmethod
    def flaky_test_live(self, execution: TestExecution):
        """
        Detect whether a given test execution is flaky and append the result to its `flakefighter_results` attribute.
        :param execution: The test execution to classify.
        """

    @abstractmethod
    def flaky_tests_post(self, run: Run):
        """
        Go through each test in the test suite and append the result to its `flakefighter_results` attribute.
        :param run: Run object representing the pytest run, with tests accessible through run.tests.
        """

    @abstractmethod
    def params(self) -> dict:
        """
        Return a dictionary of the parameters used to create the object.
        """
