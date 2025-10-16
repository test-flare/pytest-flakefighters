"""
Test DeFlaker algorithm.
"""

import os

import git
from pytest import ExitCode


def repo_name(repo: git.Repo):
    """
    Extract the name of the repo from its working dir.
    :param repo: The git repo.
    """
    return os.path.basename(repo.working_dir)


def test_real_failures_named_source_target(pytester, deflaker_repo):
    """Make sure that genuine failures are labelled as such."""

    # Add an extra commit so we can test indexing from not the most recent
    deflaker_repo.index.commit("This is an empty commit")

    commits = [commit.hexsha for commit in deflaker_repo.iter_commits("main")]

    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "-s",
        f"--source-commit={commits[1]}",
        f"--target-commit={commits[2]}",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "FAILED app.py::test_app*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."


def test_flaky_failures(pytester, flaky_triangle_repo):
    """Make sure that flaky failures are labelled as such"""

    # Add an empty commit to hide the flakiness
    # Long term, we may want to look at other ways of forcing flaky test outcomes, e.g. random seeds
    flaky_triangle_repo.index.commit("Broke the tests.")
    flaky_triangle_repo.index.commit("This is an empty commit")

    with open(os.path.join(flaky_triangle_repo.working_dir, "suffix.txt"), "w") as f:
        print("Triangle", file=f)

    result = pytester.runpytest(
        os.path.join(flaky_triangle_repo.working_dir, "triangle.py"), f"--repo={flaky_triangle_repo.working_dir}", "-s"
    )

    result.assert_outcomes(failed=2, skipped=1)
    result.stdout.fnmatch_lines(
        [
            "FLAKY triangle.py::test_eqiulateral*",
            "FLAKY triangle.py::test_isosceles*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."


def test_suppress_flaky_failures(pytester, flaky_triangle_repo):
    """Test exit code is OK when only flaky failures"""

    # Add an empty commit to hide the flakiness
    # Long term, we may want to look at other ways of forcing flaky test outcomes, e.g. random seeds
    flaky_triangle_repo.index.commit("Broke the tests.")
    flaky_triangle_repo.index.commit("This is an empty commit")

    with open(os.path.join(flaky_triangle_repo.working_dir, "suffix.txt"), "w") as f:
        print("Triangle", file=f)

    result = pytester.runpytest(
        os.path.join(flaky_triangle_repo.working_dir, "triangle.py"),
        "-s",
        "--suppress-flaky-failures-exit-code",
    )

    result.assert_outcomes(failed=2, skipped=1)
    result.stdout.fnmatch_lines(
        [
            "FLAKY triangle.py::test_eqiulateral*",
            "FLAKY triangle.py::test_isosceles*",
        ]
    )
    assert result.ret == ExitCode.OK, f"Expected exit code {ExitCode.OK} but was {result.ret}."


def test_deflaker_example(pytester, deflaker_repo):
    """Make sure that the example from the DeFlaker paper works."""

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "-s",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])
