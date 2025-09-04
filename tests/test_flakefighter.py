"""
Test DeFlaker algorithm.
"""

import os
import shutil
import pytest
import git


@pytest.fixture(scope="session", name="git_repo")
def fixture_git_repo(tmpdir_factory):
    """
    Fixture for a minimal git repo with a commit history of broken tests.
    """
    repo_root = tmpdir_factory.mktemp("repo")
    repo = git.Repo.init(repo_root)
    shutil.copy("tests/resources/triangle.txt", os.path.join(repo_root, "triangle.py"))
    shutil.copy("tests/resources/test_triangle.txt", os.path.join(repo_root, "test_triangle.py"))
    repo.index.add(["triangle.py", "test_triangle.py"])
    repo.index.commit("Initial commit of test file.")
    shutil.copy("tests/resources/triangle_failure.txt", os.path.join(repo_root, "triangle.py"))
    repo.index.add(["triangle.py", "test_triangle.py"])
    repo.index.commit("Broke the tests.")
    return repo_root


def test_files_exist(git_repo):
    """
    Test that the necessary fixture files have actually heen created.
    """
    assert os.path.exists(
        os.path.join(git_repo, "triangle.py")
    ), f"Fixture file {os.path.join(git_repo, 'triangle.py')} not present."
    assert os.path.exists(
        os.path.join(git_repo, "test_triangle.py")
    ), f"Fixture file {os.path.join(git_repo, 'test_triangle.py')} not present."


def test_bar_fixture(pytester, git_repo):
    """Make sure that pytest accepts our fixture."""

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(git_repo, "test_triangle.py"),
        f"--repo={git_repo}",
    )

    assert result.ret == 1, "Expected tests to fail"

    result.stdout.fnmatch_lines(
        [
            "Real faults ['repo0/test_triangle.py::test_eqiulateral', 'repo0/test_triangle.py::test_isosceles', "
            "'repo0/test_triangle.py::test_scalene']"
        ]
    )
