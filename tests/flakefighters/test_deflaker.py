"""
This module tests the DeFlaker flakefighter.
"""

import os

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    Test,
    TestExecution,
)
from pytest_flakefighters.flakefighters.deflaker import DeFlaker


def test_clean_repo(flaky_reruns_repo):
    """
    Test the setup of source and target commits for a clean repo (no uncommitted changes).
    """
    commits = [commit.hexsha for commit in flaky_reruns_repo.iter_commits("main")]

    deflaker = DeFlaker(True, repo_root=flaky_reruns_repo.working_dir)

    assert deflaker.source_commit == commits[1], f"Expected source commit {commits[1]} but was {deflaker.source_commit}"
    assert deflaker.target_commit == commits[0], f"Expected source commit {commits[0]} but was {deflaker.target_commit}"


def test_dirty_repo(flaky_reruns_repo):
    """
    Test the setup of source and target commits for a dirty repo (uncommitted changes).
    """
    commits = [commit.hexsha for commit in flaky_reruns_repo.iter_commits("main")]

    with open(os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"), "w") as f:
        print("print()", file=f)

    deflaker = DeFlaker(True, repo_root=flaky_reruns_repo.working_dir)

    assert deflaker.source_commit == commits[0], f"Expected source commit {commits[0]} but was {deflaker.source_commit}"
    assert deflaker.target_commit is None, f"Expected source commit None but was {deflaker.target_commit}"


def test_named_source_target(flaky_reruns_repo):
    """
    Test the setup of source and target commits when both are named.
    """

    with open(os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"), "w") as f:
        print("print()", file=f)

    flaky_reruns_repo.index.add(["flaky_reruns.py"])
    flaky_reruns_repo.index.commit("Added a print statement.")

    commits = [commit.hexsha for commit in flaky_reruns_repo.iter_commits("main")]

    deflaker = DeFlaker(
        True, repo_root=flaky_reruns_repo.working_dir, source_commit=commits[1], target_commit=commits[2]
    )

    assert deflaker.source_commit == commits[1], f"Expected source commit {commits[1]} but was {deflaker.source_commit}"
    assert deflaker.target_commit == commits[2], f"Expected source commit {commits[2]} but was {deflaker.target_commit}"


def test_line_modified_by_target_commit(flaky_reruns_repo):
    """
    Test that line_modified_by_target_commit correctly returns True.
    """
    flaky_reruns_py = os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py")
    with open(flaky_reruns_py, "a") as f:
        print("print()", file=f)

    flaky_reruns_repo.index.add(["flaky_reruns.py"])
    flaky_reruns_repo.index.commit("Added a print statement.")

    deflaker = DeFlaker(True, repo_root=flaky_reruns_repo.working_dir)
    with open(flaky_reruns_py) as f:
        lines = len(f.readlines())

    expected_lines_changed = {flaky_reruns_py: [23]}
    assert (
        deflaker.lines_changed == expected_lines_changed
    ), f"Expected lines changed to be {expected_lines_changed} but was {deflaker.lines_changed}"

    for line in range(1, lines):
        assert not deflaker.line_modified_by_target_commit(
            flaky_reruns_py, line
        ), f"Expected line {line} not to be changed"

    assert deflaker.line_modified_by_target_commit(flaky_reruns_py, lines), f"Expected line {lines} to be changed"
    assert not deflaker.line_modified_by_target_commit("spurious.py", 0), "Expected spurious.py not to be changed"


def test_flaky_test_live_false(deflaker_repo):
    """
    Test live classification of genuine failure.
    """
    deflaker = DeFlaker(run_live=True, repo_root=deflaker_repo.working_dir)
    test_execution = TestExecution(
        outcome="failed",
        coverage={
            os.path.join(deflaker_repo.working_dir, "app.py"): [1, 2, 6, 7, 8, 11, 12, 15, 16],
        },
    )
    deflaker.flaky_test_live(test_execution)
    expected = FlakefighterResult(name="DeFlaker", flaky=False)
    assert test_execution.flakefighter_results == [expected]


def test_flaky_tests_post_false(deflaker_repo):
    """
    Test same failure as test_flaky_test_live_false but as a postprocess.
    """
    deflaker = DeFlaker(run_live=True, repo_root=deflaker_repo.working_dir)
    test_execution = TestExecution(
        outcome="failed",
        coverage={
            os.path.join(deflaker_repo.working_dir, "app.py"): [1, 2, 6, 7, 8, 11, 12, 15, 16],
        },
    )
    run = Run(  # pylint: disable=E1123
        tests=[
            Test(  # pylint: disable=E1123
                name="app.py::test_app",
                executions=[test_execution],
            ),
        ]
    )
    deflaker.flaky_tests_post(run)
    expected = FlakefighterResult(name="DeFlaker", flaky=False)
    for test in run.tests:
        print(test.flakefighter_results)
    assert all(test.flakefighter_results == [expected] for test in run.tests)


def test_flaky_test_live_true(flaky_reruns_repo):
    """
    Test live classification of genuine failure.
    """
    deflaker = DeFlaker(run_live=True, repo_root=flaky_reruns_repo.working_dir)
    test_execution = TestExecution(
        outcome="failed",
        coverage={
            os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"): list(range(23)),
        },
    )
    deflaker.flaky_test_live(test_execution)
    expected = FlakefighterResult(name="DeFlaker", flaky=True)
    assert test_execution.flakefighter_results == [expected]


def test_flaky_tests_post_true(flaky_reruns_repo):
    """
    Test same failure as test_flaky_test_live_false but as a postprocess.
    """
    deflaker = DeFlaker(run_live=True, repo_root=flaky_reruns_repo.working_dir)
    test_execution = TestExecution(
        outcome="failed",
        coverage={
            os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"): list(range(23)),
        },
    )
    run = Run(  # pylint: disable=E1123
        tests=[
            Test(  # pylint: disable=E1123
                name="app.py::test_app",
                executions=[test_execution],
            ),
        ]
    )
    deflaker.flaky_tests_post(run)
    expected = FlakefighterResult(name="DeFlaker", flaky=True)
    for test in run.tests:
        print(test.flakefighter_results)
    assert all(test.flakefighter_results == [expected] for test in run.tests)
