"""
This module tests the CoverageIndependence flakefighter.
"""

import pytest

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    Test,
    TestExecution,
)
from pytest_flakefighters.flakefighters.coverage_independence import (
    CoverageIndependence,
)


def test_flaky_test_live():
    """
    Test flaky_test_live is not implemented.
    (Mainly to satisfy codecov)
    """
    coverage_independence = CoverageIndependence()
    with pytest.raises(NotImplementedError):
        coverage_independence.flaky_test_live(None)


def test_flaky_tests_post_flaky():
    """
    Test that flaky_tests_post correctly identifies a flaky test.
    """

    run = Run(  # pylint: disable=E1123
        tests=[
            Test(  # pylint: disable=E1123
                name="Test1",
                executions=[TestExecution(outcome="passed", coverage={"file1.py": [1, 2, 3, 6, 7]})],
            ),
            Test(  # pylint: disable=E1123
                name="Test2",
                executions=[TestExecution(outcome="failed", coverage={"file1.py": [1, 2, 3, 6, 7]})],
            ),
        ]
    )
    coverage_independence = CoverageIndependence()
    coverage_independence.flaky_tests_post(run)
    expected_result = FlakefighterResult(name="CoverageIndependence", flaky=True)
    assert all(expected_result in t.flakefighter_results for t in run.tests)


def test_flaky_tests_post_not_flaky():
    """
    Test that flaky_tests_post correctly identifies a non-flaky test.
    """

    run = Run(  # pylint: disable=E1123
        tests=[
            Test(  # pylint: disable=E1123
                name="Test1",
                executions=[TestExecution(outcome="passed", coverage={"file1.py": [1, 2, 3, 6, 7]})],
            ),
            Test(  # pylint: disable=E1123
                name="Test2",
                executions=[TestExecution(outcome="failed", coverage={"file1.py": [1, 2, 3, 6, 8]})],
            ),
        ]
    )
    coverage_independence = CoverageIndependence()
    coverage_independence.flaky_tests_post(run)
    expected_result = FlakefighterResult(name="CoverageIndependence", flaky=False)
    assert all(expected_result in t.flakefighter_results for t in run.tests)


def test_flaky_tests_post_flaky_executions():
    """
    Test that flaky_tests_post correctly identifies a flaky test with passing and failing executions.
    """

    run = Run(  # pylint: disable=E1123
        tests=[
            Test(  # pylint: disable=E1123
                name="Test1",
                executions=[
                    TestExecution(outcome="passed", coverage={"file1.py": [1, 2, 3, 6, 7]}),
                    TestExecution(outcome="failed", coverage={"file1.py": [1, 2, 3, 6, 7]}),
                ],
            ),
        ]
    )
    coverage_independence = CoverageIndependence()
    coverage_independence.flaky_tests_post(run)
    expected_result = FlakefighterResult(name="CoverageIndependence", flaky=True)
    assert all(expected_result in t.flakefighter_results for t in run.tests)


def test_flaky_tests_post_single_execution():
    """
    Test that flaky_tests_post gracefully handles a single execution.
    """

    run = Run(  # pylint: disable=E1123
        tests=[
            Test(  # pylint: disable=E1123
                name="Test1",
                executions=[
                    TestExecution(outcome="passed", coverage={"file1.py": [1, 2, 3, 6, 7]}),
                ],
            ),
        ]
    )
    coverage_independence = CoverageIndependence()
    coverage_independence.flaky_tests_post(run)
    assert all(t.flakefighter_results == [] for t in run.tests)
