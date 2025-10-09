"""
This module contains tests that are specific to database management.
"""

import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from pytest_flakefighter.database_management import Database, Run


def test_run_saving(pytester, deflaker_repo):
    """Test that FlakeFighter runs are saved"""

    # run pytest with the following cmd args
    assert not os.path.exists(
        os.path.join(deflaker_repo.working_dir, "flakefighter.db")
    ), "Database file should not exist in advance of running pytest"
    pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "-s",
    )
    db = Database(f"sqlite:///{os.path.join(deflaker_repo.working_dir, 'flakefighter.db')}")
    assert len(db.load_runs()) == 1, "Pytest run should have been saved"


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
    for _ in range(10):
        pytester.runpytest(os.path.join(deflaker_repo.working_dir, "app.py"), "-s", "--store-max-runs=4")
    db = Database(f"sqlite:///{os.path.join(deflaker_repo.working_dir, 'flakefighter.db')}")
    stored_runs = len(db.load_runs())
    assert stored_runs == 4, f"Should have saved 4 pytest runs but was {stored_runs}"


def test_time_immemorial(pytester, deflaker_repo):
    """Test that we only load the specified number of runs"""

    # run pytest with the following cmd args
    assert not os.path.exists(
        os.path.join(deflaker_repo.working_dir, "flakefighter.db")
    ), "Database file should not exist in advance of running pytest"
    for _ in range(5):
        pytester.runpytest(os.path.join(deflaker_repo.working_dir, "app.py"), "-s")

    db = Database(f"sqlite:///{os.path.join(deflaker_repo.working_dir, 'flakefighter.db')}")
    with Session(db.engine) as session:
        run = session.query(Run).get(1)
        run.created_at = datetime.now() - timedelta(days=2)
        session.commit()
        session.flush()
    pytester.runpytest(os.path.join(deflaker_repo.working_dir, "app.py"), "-s", "--time-immemorial=1:0:0")

    stored_runs = len(db.load_runs())
    assert stored_runs == 5, f"Should have saved 4 pytest runs but was {stored_runs}"
