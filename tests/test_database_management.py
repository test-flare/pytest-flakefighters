"""
This module contains tests that are specific to database management.
"""

import os
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from pytest_flakefighter.database_management import Database, Run, Test


def test_run_saving(pytester, flaky_triangle_repo):
    """Test that FlakeFighter runs are saved"""

    with open(os.path.join(flaky_triangle_repo.working_dir, "suffix.txt"), "w") as f:
        print("Triangle", file=f)

    # run pytest with the following cmd args
    assert not os.path.exists(
        os.path.join(flaky_triangle_repo.working_dir, "flakefighter.db")
    ), "Database file should not exist in advance of running pytest"
    pytester.runpytest(
        os.path.join(flaky_triangle_repo.working_dir, "triangle.py"),
        "-s",
        "--max-flaky-reruns=2",
    )

    db = Database(f"sqlite:///{os.path.join(flaky_triangle_repo.working_dir, 'flakefighter.db')}")
    runs = db.load_runs()

    assert len(runs) == 1, f"Expected 1 saved run but was {len(runs)}"

    run = runs[0]
    assert len(run.tests) == 3, f"Expected 3 tests but was {len(run.tests)}"

    outcomes = [[r.outcome for r in t.executions] for t in run.tests]
    assert outcomes == [
        ["failed"] * 3,  # First test failed three times
        ["failed"] * 3,  # Second test failed three times
        [],  # Third test never run because skipped
    ], f"Expected flaky class {[['failed']*3,['failed']*3, []]} but got {outcomes}"
    assert [t.flaky for t in run.tests] == [
        True,
        True,
        None,
    ], f"Expected flaky class {[True, True, None]} but got {[t.flaky for t in run.tests]}"


def test_max_load_runs(pytester, deflaker_repo):
    """Test that we only load the specified number of runs"""

    # run pytest with the following cmd args
    assert not os.path.exists(
        os.path.join(deflaker_repo.working_dir, "flakefighter.db")
    ), "Database file should not exist in advance of running pytest"
    for _ in range(5):
        pytester.runpytest(
            os.path.join(deflaker_repo.working_dir, "app.py"),
            "-s",
        )
    db = Database(f"sqlite:///{os.path.join(deflaker_repo.working_dir, 'flakefighter.db')}")
    assert len(db.load_runs()) == 5, "Should have saved 5 pytest runs"
    assert [run.id for run in db.load_runs(2)] == [
        5,
        4,
    ], "Expected to load only the 2 most recent runs with IDs 4 and 5"


def test_store_max_runs(pytester, deflaker_repo):
    """Test that we only load the specified number of runs"""

    # run pytest with the following cmd args
    assert not os.path.exists(
        os.path.join(deflaker_repo.working_dir, "flakefighter.db")
    ), "Database file should not exist in advance of running pytest"
    for _ in range(5):
        pytester.runpytest(os.path.join(deflaker_repo.working_dir, "app.py"), "-s", "--store-max-runs=4")
    db = Database(f"sqlite:///{os.path.join(deflaker_repo.working_dir, 'flakefighter.db')}")

    # Check first run with ID=1 was cleared
    with Session(db.engine) as session:
        run = session.query(Run).get(1)
        assert run is None, "Run with ID 1 should have been deleted"

    # Check it's associated Tests were cleared
    with Session(db.engine) as session:
        tests = list(session.scalars(select(Test).where(Test.run_id == 1)))
        assert len(list(tests)) == 0


def test_time_immemorial(pytester, deflaker_repo):
    """Test that we only load the specified number of runs"""

    # run pytest with the following cmd args
    assert not os.path.exists(
        os.path.join(deflaker_repo.working_dir, "flakefighter.db")
    ), "Database file should not exist in advance of running pytest"

    # Run pytest 5 times to fill up the database
    for _ in range(5):
        pytester.runpytest(os.path.join(deflaker_repo.working_dir, "app.py"), "-s")

    # Spoof the first run as being from 2 days ago
    db = Database(f"sqlite:///{os.path.join(deflaker_repo.working_dir, 'flakefighter.db')}")
    with Session(db.engine) as session:
        run = session.query(Run).get(1)
        run.created_at = datetime.now() - timedelta(days=2)
        session.commit()
        session.flush()

    # Run pytest again to clear the "old" entry with ID=1
    pytester.runpytest(os.path.join(deflaker_repo.working_dir, "app.py"), "-s", "--time-immemorial=1:0:0")

    # Check it was cleared
    with Session(db.engine) as session:
        run = session.query(Run).get(1)
        assert run is None, "Run with ID 1 should have been deleted"

    # Check it's associated Tests were cleared
    with Session(db.engine) as session:
        tests = list(session.scalars(select(Test).where(Test.run_id == 1)))
        assert len(list(tests)) == 0
