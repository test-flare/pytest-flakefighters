"""
Define fixtures and plugins.
"""

import os
import shutil
from pathlib import Path

import git
import pytest

from pytest_flakefighters.database_management import (
    TestException,
    TestExecution,
    TracebackEntry,
)

# pylint:disable=C0103
pytest_plugins = "pytester"
CURRENT_DIR = Path(__file__).parent


@pytest.fixture(scope="function", name="test_execution")
def _test_execution(flaky_reruns_repo):
    return TestExecution(
        outcome="failed",
        exception=TestException(
            name="AssertionError",
            traceback=[
                TracebackEntry(
                    id=23,
                    exception_id=1,
                    path=os.path.join(
                        flaky_reruns_repo.working_dir,
                        "venv",
                        "lib",
                        "python3.11",
                        "site-packages",
                        "_pytest",
                        "python.py",
                    ),
                    lineno=165,
                    colno=13,
                    statement="    result = testfunction(**testargs)",
                    source="""
@hookimpl(trylast=True)
def pytest_pyfunc_call(pyfuncitem: Function) -> object | None:
    testfunction = pyfuncitem.obj
    if is_async_function(testfunction):
        async_fail(pyfuncitem.nodeid)
        funcargs = pyfuncitem.funcargs
        testargs = {arg: funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
        result = testfunction(**testargs)""",
                ),
                TracebackEntry(
                    path=os.path.join(
                        flaky_reruns_repo.working_dir,
                        "flaky_reruns.py",
                    ),
                    lineno=21,
                    colno=8,
                    statement="        assert result",
                    source="""
        def test_create_or_delete(self):
            flaky = FlakyReruns("test.txt")
            result = flaky.create_or_delete()
            assert result
            """,
                ),
            ],
        ),
    )


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
