"""
Test DeFlaker algorithm.
"""

import os

import git
from pytest import ExitCode


def repo_name(repo):
    return os.path.basename(repo.working_dir)


def test_real_failures(pytester, flaky_triangle_repo):
    """Make sure that genuine failures are labelled as such."""

    result = pytester.runpytest(
        os.path.join(flaky_triangle_repo.working_dir, "triangle.py"),
        f"--repo={flaky_triangle_repo.working_dir}",
        "-s",
    )

    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(
        [
            f"FAILED {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_eqiulateral*",
            f"FAILED {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_isosceles*",
            f"FAILED {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_scalene*",
        ]
    )


def test_real_failures_named_source(pytester, flaky_triangle_repo):
    """Make sure that genuine failures are labelled as such."""

    # Add an extra commit so we can test indexing from not the most recent
    flaky_triangle_repo.index.commit("This is an empty commit")

    commits = [commit.hexsha for commit in flaky_triangle_repo.iter_commits("main")]

    result = pytester.runpytest(
        os.path.join(flaky_triangle_repo.working_dir, "triangle.py"),
        f"--repo={flaky_triangle_repo.working_dir}",
        f"--target-commit={commits[1]}",
        f"--target-commit={commits[2]}",
        "-s",
    )

    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(
        [
            f"FAILED {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_eqiulateral*",
            f"FAILED {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_isosceles*",
            f"FAILED {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_scalene*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."


def test_flaky_failures(pytester, flaky_triangle_repo):
    """Make sure that flaky failures are labelled as such"""

    # Add an empty commit to hide the flakiness
    # Long term, we may want to look at other ways of forcing flaky test outcomes, e.g. random seeds
    flaky_triangle_repo.index.commit("This is an empty commit")

    result = pytester.runpytest(
        os.path.join(flaky_triangle_repo.working_dir, "triangle.py"), f"--repo={flaky_triangle_repo.working_dir}", "-s"
    )

    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(
        [
            f"FLAKY {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_eqiulateral*",
            f"FLAKY {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_isosceles*",
            f"FLAKY {os.path.join('..',repo_name(flaky_triangle_repo), 'triangle.py')}::test_scalene*",
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
        os.path.join(deflaker_repo.working_dir, "app.py"),
        f"--repo={deflaker_repo.working_dir}",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([f"FAILED {os.path.join('..','deflaker_repo0', 'app.py')}::test_app - assert False"])
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."
