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
        "--max-reruns=3",
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


def test_invalid_deflaker(pytester, flaky_reruns_repo):
    """Test that an incorrectly specified configuration raises an error"""

    with open(os.path.join(flaky_reruns_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write("[tool.pytest.ini_options.pytest_flakefighters.flakefighters.DeFlaker]\nrun_live=false")

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--suppress-flaky-failures-exit-code",
    )
    assert result.ret == ExitCode.INTERNAL_ERROR, "No error raised"
    result.stderr.fnmatch_lines(
        ["INTERNALERROR> ValueError: Could not load flakefighter DeFlaker:run_live. Did you register its entry point?"]
    )


def test_deflaker_postprocessing(pytester, flaky_reruns_repo):
    """Test that DeFlaker still marks flaky tests when run in postprocessing mode"""

    with open(os.path.join(flaky_reruns_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write("[tool.pytest.ini_options.pytest_flakefighters.flakefighters.deflaker.DeFlaker]\nrun_live=false")

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


def test_deflaker_example_function_coverage(pytester, deflaker_repo):
    """
    Test the DeFlaker example with function coverage.
    This will show the test as flaky, since none of the function definitions have chnaged.
    """

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "--function-coverage",
        "-s",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FLAKY app.py::test_app - assert False"])
