"""
Define fixtures and plugins.
"""

import os
import shutil
from pathlib import Path

import git
import pytest

# pylint:disable=C0103
pytest_plugins = "pytester"
CURRENT_DIR = Path(__file__).parent


@pytest.fixture(scope="function", name="flaky_triangle_repo")
def fixture_flaky_triangle_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history to hide failing tests.
    """
    repo_root = tmpdir_factory.mktemp("flaky_triangle_repo")
    repo = git.Repo.init(repo_root, initial_branch="main")

    shutil.copy(os.path.join(CURRENT_DIR, "resources", "triangle.py"), os.path.join(repo_root, "triangle.py"))
    repo.index.add(["triangle.py"])
    repo.index.commit("Initial commit of test file.")
    repo.index.commit("This is an empty commit")

    os.chdir(repo_root)
    return repo


@pytest.fixture(scope="function", name="gatorgrade_repo")
def fixture_gatorgrade_repo(tmpdir_factory):
    """
    Fixture for a repo containing the gatorgrade test that broke the plugin.
    """
    repo_root = tmpdir_factory.mktemp("gatorgrade_repo")
    repo = git.Repo.init(repo_root, initial_branch="main")

    shutil.copy(
        os.path.join(CURRENT_DIR, "resources", "test_gatorgrade.py"), os.path.join(repo_root, "test_gatorgrade.py")
    )
    repo.index.add(["test_gatorgrade.py"])
    repo.index.commit("Initial commit of test file.")
    os.chdir(repo_root)
    os.mkdir("test_assignment")
    with open(os.path.join("test_assignment", "result.txt"), "w") as f:
        f.write("✓  Complete all TODOs\n✓  Use an if statement\n✓  Complete all TODOs\nPassed 3/3 (100%) of checks")
    return repo


@pytest.fixture(scope="function", name="deflaker_repo")
def fixture_deflaker_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history of broken tests.
    """
    repo_root = tmpdir_factory.mktemp("deflaker_repo")
    repo = git.Repo.init(repo_root, initial_branch="main")
    shutil.copy(os.path.join(CURRENT_DIR, "resources", "deflaker_example.py"), os.path.join(repo_root, "app.py"))
    repo.index.add(["app.py"])
    repo.index.commit("Initial commit of test file.")
    shutil.copy(os.path.join(CURRENT_DIR, "resources", "deflaker_broken.py"), os.path.join(repo_root, "app.py"))
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
        os.path.join(Path(__file__).parent, "resources", "flaky_reruns.py"), os.path.join(repo_root, "flaky_reruns.py")
    )
    repo.index.add(["flaky_reruns.py"])
    repo.index.commit("Initial commit of test file.")
    repo.index.commit("This is an empty commit")

    os.chdir(repo_root)
    return repo
