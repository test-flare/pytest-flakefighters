"""
This module implements the FlakeFighter abstract class to be extended by concrete flakefighter classes.
Each of these is a microservice which takes a failed test and classifies that failure as either genuine or flaky.
This classification can be configured to either run "live" after each test, or as a postprocessing step on the entire
test suite after it completes.
If running live, detectors are run at the end of pytest_runtest_makereport.
If running as a postprocessing step, detectors are run at the start of pytest_sessionfinish.
"""

from abc import ABC, abstractmethod

from pytest_flakefighters.database_management import Test, TestExecution


class FlakeFighter(ABC):  # pylint: disable=R0903
    """
    Abstract base class for a FlakeFighter
    :ivar run_live: Run detection "live" after each test. Otherwise run as a postprocessing step after the test suite.
    """

    def __init__(self, run_live: bool):
        self.run_live = run_live

    @abstractmethod
    def flaky_test_live(self, execution: TestExecution) -> bool:
        """
        Detect whether a given test is flaky.
        :param execution: The test execution.
        :return: `True` if a the given test is classed as flaky, and `False` otherwise.
        """

    @abstractmethod
    def flaky_tests_post(self, tests: list[Test]) -> list[bool | None]:
        """
        Detect whether tests in a given test suite are flaky.
        :param tests: The list of tests to classify.
        :return: The flaky classification of each test in order.
        `True` if a test is classed as flaky, and `False` otherwise.
        """
