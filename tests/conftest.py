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

    shutil.copy(os.path.join(CURRENT_DIR, "resources", "triangle_example.txt"), os.path.join(repo_root, "triangle.py"))
    repo.index.add(["triangle.py"])
    repo.index.commit("Initial commit of test file.")

    shutil.copy(os.path.join(CURRENT_DIR, "resources", "triangle_broken.txt"), os.path.join(repo_root, "triangle.py"))
    repo.index.add(["triangle.py"])
    os.chdir(repo_root)
    return repo


@pytest.fixture(scope="function", name="deflaker_repo")
def fixture_deflaker_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history of broken tests.
    """
    repo_root = tmpdir_factory.mktemp("deflaker_repo")
    repo = git.Repo.init(repo_root, initial_branch="main")
    shutil.copy(os.path.join(CURRENT_DIR, "resources", "deflaker_example.txt"), os.path.join(repo_root, "app.py"))
    repo.index.add(["app.py"])
    repo.index.commit("Initial commit of test file.")
    shutil.copy(os.path.join(CURRENT_DIR, "resources", "deflaker_broken.txt"), os.path.join(repo_root, "app.py"))
    repo.index.add(["app.py"])
    repo.index.commit("Broke the tests.")
    os.chdir(repo_root)
    return repo
