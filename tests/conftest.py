"""
Define fixtures and plugins.
"""

import os
import shutil

import git
import pytest

# pylint:disable=C0103
pytest_plugins = "pytester"


@pytest.fixture(scope="session", name="triangle_repo")
def fixture_triangle_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history of broken tests.
    """
    repo_root = tmpdir_factory.mktemp("triangle_repo")
    repo = git.Repo.init(repo_root)
    shutil.copy("tests/resources/triangle.txt", os.path.join(repo_root, "triangle.py"))
    shutil.copy("tests/resources/test_triangle.txt", os.path.join(repo_root, "test_triangle.py"))
    repo.index.add(["triangle.py", "test_triangle.py"])
    repo.index.commit("Initial commit of test file.")

    shutil.copy("tests/resources/triangle_failure.txt", os.path.join(repo_root, "triangle.py"))
    repo.index.add(["triangle.py", "test_triangle.py"])
    repo.index.commit("Broke the tests.")
    return repo_root


@pytest.fixture(scope="session", name="deflaker_repo")
def fixture_deflaker_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history of broken tests.
    """
    repo_root = tmpdir_factory.mktemp("deflaker_repo")
    repo = git.Repo.init(repo_root)
    shutil.copy("tests/resources/deflaker_example.txt", os.path.join(repo_root, "app.py"))
    repo.index.add(["app.py"])
    repo.index.commit("Initial commit of test file.")
    shutil.copy("tests/resources/deflaker_broken.txt", os.path.join(repo_root, "app.py"))
    repo.index.add(["app.py"])
    repo.index.commit("Broke the tests.")
    return repo_root
