"""
This module implements tests for reruning flaky failures.
"""

import os

from pytest_flakefighters.database_management import Database


def test_flaky_reruns(pytester, flaky_triangle_repo):
    """Make sure that flaky failures are labelled as such"""

    # Add an empty commit to hide the flakiness
    # Long term, we may want to look at other ways of forcing flaky test outcomes, e.g. random seeds
    flaky_triangle_repo.index.commit("Broke the tests.")
    flaky_triangle_repo.index.commit("This is an empty commit")

    with open(os.path.join(flaky_triangle_repo.working_dir, "suffix.txt"), "w") as f:
        print("Triangle", file=f)

    pytester.runpytest(
        os.path.join(flaky_triangle_repo.working_dir, "triangle.py"),
        f"--repo={flaky_triangle_repo.working_dir}",
        "-s",
        "--max-reruns=2",
    )

    db = Database(f"sqlite:///{os.path.join(flaky_triangle_repo.working_dir, 'flakefighters.db')}")
    runs = db.load_runs()
    assert len(runs) == 1, f"Should have saved 1 pytest run, saved {len(runs)}"

    tests = runs[0].tests
    assert len(tests) == 3, f"Should be 3 tests, but was {len(tests)}: {[test.name for test in tests]}"
    db.engine.dispose()
