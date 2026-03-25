"""
This module implements tests for the SFFL module.
"""

import os
from math import sqrt
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Test,
    TestExecution,
)
from pytest_flakefighters.sffl import SFFL, safe_div, total_coverage, update_covered


@pytest.fixture(name="tests")
def tests_fixture():
    """
    Simulated results of the test runs from [10.1109/TR.2013.2285319].
    """
    test_1 = Test(
        executions=[
            TestExecution(coverage={"file1": [1, 2, 3, 5, 6]}),
            TestExecution(coverage={"file1": [1, 2, 3, 4]}),
        ],
        flakefighter_results=[
            FlakefighterResult(name="dummy", flaky=True),
        ],
    )
    test_2 = Test(
        executions=[
            TestExecution(coverage={"file1": [1, 2, 3, 5, 6]}),
            TestExecution(coverage={"file1": [1, 2, 3, 4]}),
        ],
        flakefighter_results=[
            FlakefighterResult(name="dummy", flaky=False),
        ],
    )
    return [test_1, test_2]


def test_total_coverage():
    """
    Test that the total coverage is the union of all test runs.
    """
    test = Test(
        executions=[
            TestExecution(coverage={"file1": [1, 2], "file2": [3, 5]}),
            TestExecution(coverage={"file1": [3, 4]}),
        ]
    )
    assert total_coverage("", test) == {"file1": {1, 2, 3, 4}, "file2": {3, 5}}


def test_update_covered():
    """
    Test that the covered count updates as expected.
    """
    covered = {("file1", 1): 1}
    coverage = {"file1": [1, 2], "file2": [3, 5]}
    update_covered(covered, coverage)
    assert covered == {
        ("file1", 1): 2,
        ("file1", 2): 1,
        ("file2", 3): 1,
        ("file2", 5): 1,
    }


@pytest.mark.parametrize(
    ("x, y, expected"),
    [
        pytest.param(1.0, 2.0, 1.0 / 2.0, id="1/2"),
        pytest.param(0, 2.0, 0, id="0/x"),
        pytest.param(1, 0, float("inf"), id="1/0"),
        pytest.param(-1, 0, -float("inf"), id="1/0"),
        pytest.param(0, 0, 0, id="0/0"),
    ],
)
def test_safe_div(x, y, expected):
    """
    Test that safe_div works in all categories.
    """
    assert safe_div(x, y) == expected


@pytest.mark.parametrize(
    ("metric, suspiciousness"),
    [
        pytest.param("tarantula", [0.5, 0.5, 0.5, 0, 0, 0], id="tarantula"),
        pytest.param("ochiai", [1 / sqrt(2), 1 / sqrt(2), 1 / sqrt(2), 0, 0, 0], id="ochiai"),
        pytest.param("dstar", [1.0, 1.0, 1.0, 0, 0, 0], id="dstar"),
        pytest.param("op2", [0.5, 0.5, 0.5, -0.5, -0.5, -0.5], id="op2"),
        pytest.param("barinel", [0.5, 0.5, 0.5, 0, 0, 0], id="barinel"),
    ],
)
def test_suspiciousness_scores(tests, metric, suspiciousness):
    """
    Test all the suspiciousness metrics work as expected.
    """
    with TemporaryDirectory() as tempdir:
        output_file = os.path.join(tempdir, f"{metric}.csv")
        sffl = SFFL(root="", metric=metric, output_file=output_file)
        expected = pd.DataFrame({"file": ["file1"] * 6, "line": range(1, 7), "suspiciousness": suspiciousness})
        sffl.rank(tests)
        assert os.path.exists(output_file)
        pd.testing.assert_frame_equal(pd.read_csv(output_file, index_col=0), expected)
