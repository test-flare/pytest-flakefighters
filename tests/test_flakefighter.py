"""
Test DeFlaker algorithm.
"""

import os

import git
from pytest import ExitCode


def test_files_exist(flaky_triangle_repo, deflaker_repo):
    """
    Test that the necessary fixture files have actually heen created.
    """
    assert os.path.exists(
        os.path.join(flaky_triangle_repo, "triangle.py")
    ), f"Fixture file {os.path.join(flaky_triangle_repo, 'triangle.py')} not present."
    assert os.path.exists(
        os.path.join(deflaker_repo, "app.py")
    ), f"Fixture file {os.path.join(deflaker_repo, 'app.py')} not present."


def test_real_failures(pytester, flaky_triangle_repo):
    """Make sure that genuine failures are labelled as such."""
    repo = git.Repo(flaky_triangle_repo)
    commits = [commit.hexsha for commit in repo.iter_commits("main")]

    result = pytester.runpytest(
        os.path.join(flaky_triangle_repo, "triangle.py"),
        f"--repo={flaky_triangle_repo}",
        f"--commit={commits[1]}",
        "-s",
    )

    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(
        [
            f"FAILED {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_eqiulateral*",
            f"FAILED {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_isosceles*",
            f"FAILED {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_scalene*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."


def test_flaky_failures(pytester, flaky_triangle_repo):
    """Make sure that flaky failures are labelled as such"""

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(flaky_triangle_repo, "triangle.py"),
        f"--repo={flaky_triangle_repo}",
        "-s",
    )

    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(
        [
            f"FLAKY {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_eqiulateral*",
            f"FLAKY {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_isosceles*",
            f"FLAKY {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_scalene*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."


def test_suppress_flaky_failures(pytester, flaky_triangle_repo):
    """Make sure that flaky failures are labelled as such"""

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(flaky_triangle_repo, "triangle.py"),
        f"--repo={flaky_triangle_repo}",
        "--suppress-flaky-failures-exit-code",
        "-s",
    )

    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(
        [
            f"FLAKY {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_eqiulateral*",
            f"FLAKY {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_isosceles*",
            f"FLAKY {os.path.join('..','flaky_triangle_repo0', 'triangle.py')}::test_scalene*",
        ]
    )
    assert result.ret == ExitCode.OK, f"Expected exit code {ExitCode.OK} but was {result.ret}."


def test_deflaker_example(pytester, deflaker_repo):
    """Make sure that pytest accepts our fixture."""

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(deflaker_repo, "app.py"),
        f"--repo={deflaker_repo}",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([f"FAILED {os.path.join('..','deflaker_repo0', 'app.py')}::test_app - assert False"])
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."
