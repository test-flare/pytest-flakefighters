"""
Define fixtures and plugins.
"""

import os
import shutil
import sqlite3
from pathlib import Path

import git
import pytest

# pylint:disable=C0103
pytest_plugins = "pytester"
CURRENT_DIR = Path(__file__).parent
collect_ignore = ["resources"]


@pytest.fixture(autouse=True)
def _close_leaked_sqlite_connections(monkeypatch):
    """
    Close any sqlite3 connections opened during a test.

    In-process pytest runs can abandon Database engines (e.g. when an inner run
    fails during configuration), leaving sqlite3 connections open until the
    garbage collector collects them, which emits a ResourceWarning. Tracking
    connections as they are created and closing them at the end of each test
    prevents those warnings deterministically.
    """
    connections = []
    original_connect = sqlite3.dbapi2.connect

    def _tracking_connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connections.append(connection)
        return connection

    # SQLAlchemy creates connections via sqlite3.dbapi2.connect, so patch both names.
    monkeypatch.setattr(sqlite3, "connect", _tracking_connect)
    monkeypatch.setattr(sqlite3.dbapi2, "connect", _tracking_connect)
    yield
    for connection in connections:
        connection.close()


@pytest.fixture(scope="function", name="flaky_triangle_repo")
def fixture_flaky_triangle_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history to hide failing tests.
    """
    repo_root = tmpdir_factory.mktemp("flaky_triangle_repo")
    repo = git.Repo.init(repo_root, initial_branch="main")

    shutil.copy(
        os.path.join(CURRENT_DIR, "resources", "triangle.py"),
        os.path.join(repo_root, "triangle.py"),
    )
    repo.index.add(["triangle.py"])
    repo.index.commit("Initial commit of test file.")
    repo.index.commit("This is an empty commit")

    os.chdir(repo_root)
    return repo


@pytest.fixture(scope="function", name="gatorgrade_dir")
def fixture_gatorgrade_repo(tmpdir_factory):
    """
    Fixture for a repo containing the gatorgrade test that broke the plugin.
    """
    repo_root = tmpdir_factory.mktemp("gatorgrade_repo")
    shutil.copy(
        os.path.join(CURRENT_DIR, "resources", "gatorgrade.py"),
        os.path.join(repo_root, "gatorgrade.py"),
    )
    os.chdir(repo_root)
    os.mkdir("test_assignment")
    with open(os.path.join("test_assignment", "result.txt"), "w", encoding="utf8") as f:
        f.write(
            "✓  Complete all TODOs\n✓  Use an if statement\n✓  Complete all TODOs\nPassed 3/3 (100%) of checks"
        )
    return repo_root


@pytest.fixture(scope="function", name="diff_cov_repo")
def fixture_diff_cov_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history of broken tests.
    """
    repo_root = tmpdir_factory.mktemp("diff_cov_repo")
    repo = git.Repo.init(repo_root, initial_branch="main")
    shutil.copy(
        os.path.join(CURRENT_DIR, "resources", "diff_cov_example.py"),
        os.path.join(repo_root, "app.py"),
    )
    repo.index.add(["app.py"])
    repo.index.commit("Initial commit of test file.")
    shutil.copy(
        os.path.join(CURRENT_DIR, "resources", "diff_cov_broken.py"),
        os.path.join(repo_root, "app.py"),
    )
    repo.index.add(["app.py"])
    repo.index.commit("Broke the tests.")
    os.chdir(repo_root)
    return repo


@pytest.fixture(scope="function", name="flaky_reruns_repo")
def fixture_flaky_reruns_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history to hide failing tests.
    """
    repo_root = tmpdir_factory.mktemp("flaky_reruns_repo")
    repo = git.Repo.init(repo_root, initial_branch="main")

    shutil.copy(
        os.path.join(Path(__file__).parent, "resources", "flaky_reruns.py"),
        os.path.join(repo_root, "flaky_reruns.py"),
    )
    repo.index.add(["flaky_reruns.py"])
    repo.index.commit("Initial commit of test file.")
    repo.index.commit("This is an empty commit")

    os.chdir(repo_root)
    return repo


@pytest.fixture(scope="function", name="sffl_repo")
def fixture_sffl_repo(tmpdir_factory):
    """
    Fixture for the SFFL example.
    """
    repo_root = tmpdir_factory.mktemp("sffl_repo")
    repo = git.Repo.init(repo_root, initial_branch="main")

    shutil.copy(
        os.path.join(Path(__file__).parent, "resources", "sffl_example.py"),
        os.path.join(repo_root, "sffl_example.py"),
    )
    shutil.copy(
        os.path.join(Path(__file__).parent, "resources", "test_sffl_example.py"),
        os.path.join(repo_root, "test_sffl_example.py"),
    )
    repo.index.add(["sffl_example.py"])
    repo.index.add(["test_sffl_example.py"])
    repo.index.commit("Initial commit of test file.")
    repo.index.commit("This is an empty commit")

    os.chdir(repo_root)
    return repo
