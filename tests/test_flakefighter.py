import git
import shutil
import os
import pytest


@pytest.fixture(scope="session")
def git_repo(tmpdir_factory):
    repo_root = tmpdir_factory.mktemp("repo")
    repo = git.Repo.init(repo_root)
    shutil.copy("tests/resources/triangle.txt", os.path.join(repo_root, "triangle.py"))
    shutil.copy(
        "tests/resources/test_triangle.txt", os.path.join(repo_root, "test_triangle.py")
    )
    repo.index.add(["triangle.py", "test_triangle.py"])
    repo.index.commit("Initial commit of test file.")
    shutil.copy(
        "tests/resources/triangle_failure.txt", os.path.join(repo_root, "triangle.py")
    )
    repo.index.add(["triangle.py", "test_triangle.py"])
    repo.index.commit("Broke the tests.")
    return repo_root


def test_files_exist(git_repo):
    assert os.path.exists(os.path.join(git_repo, "triangle.py"))
    assert os.path.exists(os.path.join(git_repo, "test_triangle.py"))


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
            "Real faults ['repo0/test_triangle.py::test_eqiulateral', 'repo0/test_triangle.py::test_isosceles', 'repo0/test_triangle.py::test_scalene']"
        ]
    )
