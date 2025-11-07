"""
Test DeFlaker algorithm.
"""

import os

from pytest import ExitCode


def test_real_failures(pytester, deflaker_repo):
    """Make sure that genuine failures are labelled as such."""

    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "-s",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "FAILED app.py::test_app*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."


def test_rerun_flaky_failures(pytester, flaky_reruns_repo):
    """Test exit code is OK when only flaky failures"""

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--max-flaky-reruns=3",
    )

    result.assert_outcomes(passed=1)
    assert result.ret == ExitCode.OK, f"Expected exit code {ExitCode.OK} but was {result.ret}."


def test_suppress_flaky_failures(pytester, flaky_reruns_repo):
    """Test exit code is OK when only flaky failures"""

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--suppress-flaky-failures-exit-code",
    )

    result.assert_outcomes(failed=1)
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
