"""
This module implements tests for reruning flaky failures.
"""

import os
import shutil

from pytest_flakefighters.database_management import Database

from .conftest import CURRENT_DIR


def test_flaky_reruns(pytester, flaky_reruns_repo):
    """Make sure that flaky failures are rerun"""

    pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        f"--root={flaky_reruns_repo.working_dir}",
        "-s",
        "--flakefighters",
        "--max-reruns=2",
    )
    db = Database(f"sqlite:///{os.path.join(flaky_reruns_repo.working_dir, 'flakefighters.db')}")
    runs = db.load_runs()
    assert len(runs) == 1, f"Should have saved 1 pytest run, saved {len(runs)}"

    tests = runs[0].tests
    assert len(tests) == 1, f"Should be 1 test, but was {len(tests)}: {[test.name for test in tests]}"
    assert len(tests[0].executions) == 2, f"Should be 2 executions, but was {len(tests[0].executions)}"
    db.engine.dispose()


def test_flaky_reruns_second_time_lucky(pytester, flaky_reruns_repo):
    """Make sure that tests are not rerun once they have passed"""

    pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        f"--root={flaky_reruns_repo.working_dir}",
        "-s",
        "--flakefighters",
        "--max-reruns=3",
    )

    db = Database(f"sqlite:///{os.path.join(flaky_reruns_repo.working_dir, 'flakefighters.db')}")
    runs = db.load_runs()
    assert len(runs) == 1, f"Should have saved 1 pytest run, saved {len(runs)}"

    tests = runs[0].tests
    assert len(tests) == 1, f"Should be 1 test, but was {len(tests)}: {[test.name for test in tests]}"
    assert len(tests[0].executions) == 2, f"Should be 2 executions, but was {len(tests[0].executions)}"
    db.engine.dispose()


def test_previously_flaky(pytester, flaky_reruns_repo):
    """Make sure that flaky failures are correctly rerun"""

    pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        f"--root={flaky_reruns_repo.working_dir}",
        "-s",
        "--flakefighters",
    )

    pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        f"--root={flaky_reruns_repo.working_dir}",
        "-s",
        "--flakefighters",
        "--max-reruns=1",
        "--rerun-strategy=PREVIOUSLY_FLAKY",
    )

    db = Database(f"sqlite:///{os.path.join(flaky_reruns_repo.working_dir, 'flakefighters.db')}")
    runs = sorted(db.load_runs(), key=lambda run: run.id)
    assert len(runs) == 2, f"Should have saved 2 pytest runs, saved {len(runs)}"

    tests = runs[0].tests
    assert len(tests) == 1, f"First run should be 1 test, but was {len(tests)}: {[test.name for test in tests]}"
    assert len(tests[0].executions) == 1, f"First run should be 1 execution, but was {len(tests[0].executions)}"

    tests = runs[1].tests

    assert len(tests) == 1, f"Second run should be 1 test, but was {len(tests)}: {[test.name for test in tests]}"
    assert len(tests[0].executions) == 2, f"Second run should be 2 executions, but was {len(tests[0].executions)}"
    db.engine.dispose()


def test_previously_flaky_no_rerun(pytester, deflaker_repo):
    """Make sure that flaky failures are correctly rerun"""

    pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        f"--root={deflaker_repo.working_dir}",
        "-s",
        "--flakefighters",
    )

    pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        f"--root={deflaker_repo.working_dir}",
        "-s",
        "--flakefighters",
        "--max-reruns=1",
        "--rerun-strategy=PREVIOUSLY_FLAKY",
    )

    db = Database(f"sqlite:///{os.path.join(deflaker_repo.working_dir, 'flakefighters.db')}")
    runs = db.load_runs()
    assert len(runs) == 2, f"Should have saved 2 pytest runs, saved {len(runs)}"

    tests = runs[0].tests
    assert len(tests) == 1, f"First run should be 1 test, but was {len(tests)}: {[test.name for test in tests]}"
    assert len(tests[0].executions) == 1, f"First run should be 1 execution, but was {len(tests[0].executions)}"
    tests = runs[0].tests
    assert len(tests) == 1, f"Second run should be 1 test, but was {len(tests)}: {[test.name for test in tests]}"
    assert len(tests[0].executions) == 1, f"Second run should be 1 execution, but was {len(tests[0].executions)}"
    db.engine.dispose()


def test_rerun_all(pytester, flaky_reruns_repo):
    """Make sure that flaky failures are correctly rerun"""

    shutil.copy(
        os.path.join(CURRENT_DIR, "resources", "pass_fail_flaky.py"),
        os.path.join(flaky_reruns_repo.working_dir, "pass_fail_flaky.py"),
    )

    pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "pass_fail_flaky.py"),
        f"--root={flaky_reruns_repo.working_dir}",
        "-s",
        "--flakefighters",
        "--max-reruns=1",
        "--rerun-strategy=ALL",
    )

    db = Database(f"sqlite:///{os.path.join(flaky_reruns_repo.working_dir, 'flakefighters.db')}")
    runs = db.load_runs()
    assert len(runs) == 1, f"Should have saved 1 pytest run, saved {len(runs)}"

    tests = runs[0].tests
    assert len(tests) == 3, f"Should be 3 tests, but was {len(tests)}: {[test.name for test in tests]}"

    assert all(len(test.executions) == 2 for test in tests), "Every test should have 2 executions"
    db.engine.dispose()
