import os

from pytest_flakefighter.database_management import Database


def test_run_saving(pytester, deflaker_repo):
    """Test that FlakeFighter runs are saved"""

    # run pytest with the following cmd args
    assert not os.path.exists(
        os.path.join(deflaker_repo.working_dir, "flakefighter.db")
    ), "Database file should not exist in advance of running pytest"
    pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
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
        )
    db = Database(f"sqlite:///{os.path.join(deflaker_repo.working_dir, 'flakefighter.db')}")
    assert len(db.load_runs()) == 5, "Should have saved 5 pytest runs"
    assert [run.id for run in db.load_runs(2)] == [
        5,
        4,
    ], "Expected to load only the 2 most recent runs with IDs 4 and 5"
