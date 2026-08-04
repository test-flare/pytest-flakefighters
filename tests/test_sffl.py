"""
This module implements tests for the SFFL module.
"""

import os
import pathlib
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
            TestExecution(coverage={"file1.py": [1, 2, 3, 5, 6], "test_file1.py": [2, 3, 4]}),
            TestExecution(coverage={"file1.py": [1, 2, 3, 4], "test_file1.py": [2, 3, 4]}),
        ],
        flakefighter_results=[
            FlakefighterResult(name="dummy", flaky=True),
        ],
        fspath="test_file1.py",
    )
    test_2 = Test(
        executions=[
            TestExecution(coverage={"file1.py": [1, 2, 3, 5, 6], "test_file1.py": [5, 6, 7]}),
            TestExecution(coverage={"file1.py": [1, 2, 3, 4], "test_file1.py": [5, 6, 7]}),
        ],
        flakefighter_results=[
            FlakefighterResult(name="dummy", flaky=False),
        ],
        fspath="test_file1.py",
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
    ("metric, include_test_code"),
    [
        # Source code only
        pytest.param("tarantula", False, id="tarantula-source-only"),
        pytest.param("ochiai", False, id="ochiai-source-only"),
        pytest.param("dstar", False, id="dstar-source-only"),
        pytest.param("op2", False, id="op2-source-only"),
        pytest.param("barinel", False, id="barinel-source-only"),
        # Include test code
        pytest.param("tarantula", True, id="tarantula-source-test"),
        pytest.param("ochiai", True, id="ochiai-source-test"),
        pytest.param("dstar", True, id="dstar-source-test"),
        pytest.param("op2", True, id="op2-source-test"),
        pytest.param("barinel", True, id="barinel-source-test"),
    ],
)
def test_suspiciousness_scores(tests, metric, include_test_code):
    """
    Test all the suspiciousness metrics work as expected.
    """
    with TemporaryDirectory() as tempdir:
        output_file = os.path.join(tempdir, f"{metric}.csv")
        sffl = SFFL(root="", metric=metric, output_file=output_file, include_test_code=include_test_code)
        sffl.rank(tests)
        assert os.path.exists(output_file)
        expected = pd.read_csv(
            os.path.join(
                pathlib.Path(__file__).parent.resolve(),
                "resources",
                "expected_sffl_results",
                f"{metric}_{'test' if include_test_code else 'source'}.csv",
            ),
            index_col=0,
        )
        calculated = pd.read_csv(output_file, index_col=0)
        pd.testing.assert_frame_equal(calculated, expected)
