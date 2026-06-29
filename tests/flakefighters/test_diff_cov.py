"""
This module tests the differential coverage flakefighter.
"""

import os
from tempfile import TemporaryDirectory

import pytest

from pytest_flakefighters.database_management import (
    Database,
    FlakefighterResult,
    Run,
    Test,
    TestExecution,
)
from pytest_flakefighters.flakefighters.diff_cov import DiffCov


@pytest.fixture(name="temp_db")
def _temp_db():
    with TemporaryDirectory() as tempdir:
        db_path = f"sqlite:///{tempdir}/test.db"
        db = Database(db_path)
        yield db
        db.engine.dispose()


@pytest.mark.parametrize("run_live", [True, False])
def test_from_config_params(flaky_reruns_repo, temp_db, run_live):
    """
    Test that from_config generates the same result as a direct call
    """
    commits = [commit.hexsha for commit in flaky_reruns_repo.iter_commits("main")]

    source_run = Run(commit_sha=commits[1])
    temp_db.save(source_run)

    from_config = DiffCov.from_config(
        {
            "run_live": run_live,
            "root": flaky_reruns_repo.working_dir,
            "source_commit": commits[1],
            "target_commit": commits[0],
            "database": temp_db,
        }
    )
    init = DiffCov(
        run_live=run_live,
        source_runs=[source_run],
        root=flaky_reruns_repo.working_dir,
        source_commit=commits[1],
        target_commit=commits[0],
    )
    assert from_config.run_live == init.run_live
    assert from_config.repo_root == init.repo_root
    assert from_config.source_commit == init.source_commit
    assert from_config.target_commit == init.target_commit
    assert from_config.params() == init.params()


def test_no_previous_runs(flaky_reruns_repo, temp_db):
    """
    Test that empty db raises an error when source commit is specified.
    """
    commits = [commit.hexsha for commit in flaky_reruns_repo.iter_commits("main")]
    with pytest.raises(ValueError):
        DiffCov.from_config(
            {
                "run_live": True,
                "root": flaky_reruns_repo.working_dir,
                "source_commit": commits[1],
                "target_commit": commits[0],
                "database": temp_db,
            }
        )


def test_clean_repo(flaky_reruns_repo):
    """
    Test the setup of source and target commits for a clean repo (no uncommitted changes).
    """
    commits = [commit.hexsha for commit in flaky_reruns_repo.iter_commits("main")]

    diff_cov = DiffCov(True, source_runs=[], root=flaky_reruns_repo.working_dir)

    assert diff_cov.source_commit == commits[1], f"Expected source commit {commits[1]} but was {diff_cov.source_commit}"
    assert diff_cov.target_commit == commits[0], f"Expected source commit {commits[0]} but was {diff_cov.target_commit}"


def test_dirty_repo(flaky_reruns_repo):
    """
    Test the setup of source and target commits for a dirty repo (uncommitted changes).
    """
    commits = [commit.hexsha for commit in flaky_reruns_repo.iter_commits("main")]

    with open(os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"), "w") as f:
        print("print()", file=f)

    diff_cov = DiffCov(True, source_runs=[], root=flaky_reruns_repo.working_dir)

    assert diff_cov.source_commit == commits[0], f"Expected source commit {commits[0]} but was {diff_cov.source_commit}"
    assert diff_cov.target_commit is None, f"Expected source commit None but was {diff_cov.target_commit}"


@pytest.mark.parametrize(
    ("previous_outcome, current_outcome"),
    [
        pytest.param("passed", "passed", id="passed both times"),
        pytest.param("passed", "failed", id="transition from passing to failing"),
        pytest.param("failed", "passed", id="transition from failing to passing"),
        pytest.param("failed", "failed", id="failed both times"),
    ],
)
def test_previous_runs(flaky_reruns_repo, previous_outcome, current_outcome):
    """
    Test that flaky tests are correctly identified based on previous outcome.
    """
    coverage = {
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"): [1, 4, 6, 9, 10, 11, 12, 14],
    }
    execution = TestExecution(outcome=current_outcome, coverage=coverage)
    Test(name="", executions=[execution])
    diff_cov = DiffCov(
        run_live=True,  # Doesn't matter since we're calling flaky_test_live directly
        source_runs=[
            Run(tests=[Test(name="", executions=[TestExecution(outcome=previous_outcome, coverage=coverage)])])
        ],
        root=flaky_reruns_repo.working_dir,
    )
    diff_cov.flaky_test_live(execution)
    [outcome] = execution.flakefighter_results
    assert outcome.flaky == (previous_outcome != current_outcome)


def test_new_test_preserves_original_results(flaky_reruns_repo):
    """
    Test the setup of source and target commits for a dirty repo (uncommitted changes).
    """

    diff_cov = DiffCov(True, source_runs=[], root=flaky_reruns_repo.working_dir)
    test_execution = TestExecution(
        outcome="failed",
        coverage={
            os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"): [1, 4, 6, 9, 10, 11, 12],
        },
    )
    Test(  # pylint: disable=E1123
        name="test_create_or_delete",
        fspath=os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        line_no=9,
        executions=[test_execution],
    )
    diff_cov.flaky_test_live(test_execution)
    expected = FlakefighterResult(name="DiffCov", flaky=True)
    assert test_execution.flakefighter_results == [
        expected
    ], "Expected original run of test_create_or_delete to be flaky"

    # Add a new test and check that test_create_or_delete is still flaky
    with open(os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"), "w") as f:
        print("def test_fail(self):\n    assert False", file=f)

    test_execution.flakefighter_results = []
    test_execution.coverage = {
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"): [1, 4, 6, 9, 10, 11, 12, 14],
    }
    diff_cov.flaky_test_live(test_execution)
    assert test_execution.flakefighter_results == [expected], "Expected second run of test_create_or_delete to be flaky"


def test_named_source_target(flaky_reruns_repo):
    """
    Test the setup of source and target commits when both are named.
    """

    with open(os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"), "w") as f:
        print("print()", file=f)

    flaky_reruns_repo.index.add(["flaky_reruns.py"])
    flaky_reruns_repo.index.commit("Added a print statement.")

    commits = [commit.hexsha for commit in flaky_reruns_repo.iter_commits("main")]

    diff_cov = DiffCov(
        True, source_runs=[], root=flaky_reruns_repo.working_dir, source_commit=commits[1], target_commit=commits[2]
    )

    assert diff_cov.source_commit == commits[1], f"Expected source commit {commits[1]} but was {diff_cov.source_commit}"
    assert diff_cov.target_commit == commits[2], f"Expected source commit {commits[2]} but was {diff_cov.target_commit}"


def test_line_modified_by_target_commit(flaky_reruns_repo):
    """
    Test that line_modified_by_target_commit correctly returns True.
    """
    flaky_reruns_py = os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py")
    with open(flaky_reruns_py, "a") as f:
        print("print()", file=f)

    flaky_reruns_repo.index.add(["flaky_reruns.py"])
    flaky_reruns_repo.index.commit("Added a print statement.")

    diff_cov = DiffCov(True, source_runs=[], root=flaky_reruns_repo.working_dir)
    with open(flaky_reruns_py) as f:
        lines = len(f.readlines())

    expected_lines_changed = {flaky_reruns_py: [23]}
    assert (
        diff_cov.lines_changed == expected_lines_changed
    ), f"Expected lines changed to be {expected_lines_changed} but was {diff_cov.lines_changed}"

    for line in range(1, lines):
        assert not diff_cov.line_modified_by_target_commit(
            flaky_reruns_py, line
        ), f"Expected line {line} not to be changed"

    assert diff_cov.line_modified_by_target_commit(flaky_reruns_py, lines), f"Expected line {lines} to be changed"
    assert not diff_cov.line_modified_by_target_commit("spurious.py", 0), "Expected spurious.py not to be changed"


def test_flaky_test_live_false(diff_cov_repo):
    """
    Test live classification of genuine failure.
    """
    diff_cov = DiffCov(run_live=True, source_runs=[], root=diff_cov_repo.working_dir)
    test_execution = TestExecution(
        outcome="failed",
        coverage={
            os.path.join(diff_cov_repo.working_dir, "app.py"): [1, 2, 6, 7, 8, 11, 12, 15, 16],
        },
    )
    Test(  # pylint: disable=E1123
        name="test_app",
        fspath=os.path.join(diff_cov_repo.working_dir, "diff_cov_example.py"),
        line_no=15,
        executions=[test_execution],
    )
    diff_cov.flaky_test_live(test_execution)
    expected = FlakefighterResult(name="DiffCov", flaky=False)
    assert test_execution.flakefighter_results == [expected]


def test_flaky_tests_post_false(diff_cov_repo):
    """
    Test same failure as test_flaky_test_live_false but as a postprocess.
    """
    diff_cov = DiffCov(run_live=True, source_runs=[], root=diff_cov_repo.working_dir)
    test_execution = TestExecution(
        outcome="failed",
        coverage={
            os.path.join(diff_cov_repo.working_dir, "app.py"): [1, 2, 6, 7, 8, 11, 12, 15, 16],
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
    diff_cov.flaky_tests_post(run)
    expected = FlakefighterResult(name="DiffCov", flaky=False)
    assert all(execution.flakefighter_results == [expected] for test in run.tests for execution in test.executions)


def test_flaky_test_live_true(flaky_reruns_repo):
    """
    Test live classification of genuine failure.
    """
    diff_cov = DiffCov(run_live=True, source_runs=[], root=flaky_reruns_repo.working_dir)
    test_execution = TestExecution(
        outcome="failed",
        coverage={
            os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"): list(range(23)),
        },
    )
    diff_cov.flaky_test_live(test_execution)
    expected = FlakefighterResult(name="DiffCov", flaky=True)
    assert test_execution.flakefighter_results == [expected]


def test_flaky_tests_post_true(flaky_reruns_repo):
    """
    Test same failure as test_flaky_test_live_false but as a postprocess.
    """
    diff_cov = DiffCov(run_live=True, source_runs=[], root=flaky_reruns_repo.working_dir)
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
    diff_cov.flaky_tests_post(run)
    expected = FlakefighterResult(name="DiffCov", flaky=True)
    for test in run.tests:
        print(test.flakefighter_results)
    assert all(execution.flakefighter_results == [expected] for test in run.tests for execution in test.executions)
