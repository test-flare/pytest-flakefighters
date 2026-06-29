"""
Test end to end runs.
"""

import json
import os
from math import sqrt

import pandas as pd
from pytest import ExitCode


def test_real_failures(pytester, diff_cov_repo):
    """Make sure that genuine failures are labelled as such."""

    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "-s",
        "--flakefighters",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "FAILED app.py::test_app*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, (
        f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."
    )


def test_real_failures_non_py_file_changed(pytester, diff_cov_repo):
    """Make sure that genuine failures are labelled as such."""

    # Create a spurious text file to make sure that this doesn't cause errors
    # e.g. when trying to parse source files
    with open(os.path.join(diff_cov_repo.working_dir, "test.txt"), "w") as f:
        f.write("Hello world")

    diff_cov_repo.index.add(["test.txt"])
    diff_cov_repo.index.commit("Added a new text file.")

    with open(os.path.join(diff_cov_repo.working_dir, "test.txt"), "a") as f:
        f.write("Hello world!")

    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "-s",
        "--flakefighters",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "FLAKY app.py::test_app*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, (
        f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."
    )


def test_rerun_flaky_failures(pytester, flaky_reruns_repo):
    """Test exit code is OK when only flaky failures"""

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--flakefighters",
        "--max-reruns=3",
    )

    result.assert_outcomes(passed=1)
    assert result.ret == ExitCode.OK, (
        f"Expected exit code {ExitCode.OK} but was {result.ret}."
    )


def test_suppress_flaky_failures(pytester, flaky_reruns_repo):
    """Test exit code is OK when only flaky failures"""

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--flakefighters",
        "--suppress-flaky-failures-exit-code",
    )

    result.assert_outcomes(failed=1)
    assert result.ret == ExitCode.OK, (
        f"Expected exit code {ExitCode.OK} but was {result.ret}."
    )


def test_invalid_diff_cov(pytester, flaky_reruns_repo):
    """Test that an incorrectly specified configuration raises an error"""

    with open(os.path.join(flaky_reruns_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.DiffCov]\nrun_live=false"
        )

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--flakefighters",
        "--suppress-flaky-failures-exit-code",
    )
    assert result.ret == ExitCode.INTERNAL_ERROR, "No error raised"
    result.stderr.fnmatch_lines(
        [
            "INTERNALERROR> ValueError: Could not load flakefighter DiffCov:run_live. Did you register its entry point?"
        ]
    )


def test_diff_cov_postprocessing(pytester, flaky_reruns_repo):
    """Test that DiffCov still marks flaky tests when run in postprocessing mode"""

    with open(os.path.join(flaky_reruns_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.diff_cov.DiffCov]\nrun_live=false"
        )

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--flakefighters",
        "--suppress-flaky-failures-exit-code",
    )

    result.assert_outcomes(failed=1)
    assert result.ret == ExitCode.OK, (
        f"Expected exit code {ExitCode.OK} but was {result.ret}."
    )


def test_diff_cov_example(pytester, diff_cov_repo):
    """Make sure that the example from the DiffCov paper works."""

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "-s",
        "--flakefighters",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])


def test_diff_cov_example_function_coverage(pytester, diff_cov_repo):
    """
    Test the DiffCov example with function coverage.
    This will show the test as flaky, since none of the function definitions have chnaged.
    """

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "--function-coverage",
        "-s",
        "--flakefighters",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FLAKY app.py::test_app - assert False"])


def test_html_report(pytester, diff_cov_repo):
    """
    Test that an html report is produced.
    """

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "--html=report.html",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])

    assert os.path.exists(os.path.join(diff_cov_repo.working_dir, "report.html")), (
        "Expected report.html to exist but it did not."
    )

    # Test that the DiffCov result is in the file and reports a genuine fault
    with open(os.path.join(diff_cov_repo.working_dir, "report.html")) as f:
        assert any(
            "&lt;li&gt;&lt;strong&gt;DiffCov:&lt;/strong&gt; genuine&lt;" in line
            for line in f
        )


def test_xml_report(pytester, diff_cov_repo):
    """
    Test that an xml report is produced.
    """

    with open(os.path.join(diff_cov_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.coverage_independence.CoverageIndependence]\n"
        )
        f.write("run_live=true\n")
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.diff_cov.DiffCov]\n"
        )
        f.write("run_live=true\n")

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "--junitxml=report.xml",
        "--max-reruns=2",
        "--rerun-strategy=ALL",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])

    assert os.path.exists(os.path.join(diff_cov_repo.working_dir, "report.xml")), (
        "Expected report.xml to exist but it did not."
    )

    # Test that the DiffCov result is in the file and reports a genuine fault
    with open(os.path.join(diff_cov_repo.working_dir, "report.xml")) as f:
        assert any("<DiffCov>genuine</DiffCov>" in line for line in f)
    with open(os.path.join(diff_cov_repo.working_dir, "report.xml")) as f:
        assert any(
            "<CoverageIndependence>genuine</CoverageIndependence>" in line for line in f
        )


def test_json_report(pytester, diff_cov_repo):
    """
    Test that an json report is produced.
    """

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "--json-report",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])

    assert os.path.exists(os.path.join(diff_cov_repo.working_dir, ".report.json")), (
        "Expected .report.json to exist but it did not."
    )

    with open(os.path.join(diff_cov_repo.working_dir, ".report.json")) as f:
        tests = json.load(f)["tests"]
        assert len(tests) == 1, f"Expected only one test but found {len(tests)}"
        assert tests[0]["call"]["metadata"]["executions"][0][
            "flakefighter_results"
        ] == {
            "DiffCov": "genuine",
        }


def test_display_verdicts(pytester, diff_cov_repo):
    """
    Test that outcomes are displayed to terminal.
    """

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "--display-verdicts",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])
    result.stdout.fnmatch_lines(["  DiffCov: genuine"])


def test_display_test_level_verdicts(pytester, diff_cov_repo):
    """
    Test that outcomes are displayed to terminal.
    """

    with open(os.path.join(diff_cov_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.coverage_independence.CoverageIndependence]\n"
        )
        f.write("run_live=true\n")
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.diff_cov.DiffCov]\n"
        )
        f.write("run_live=true\n")

    result = pytester.runpytest(
        os.path.join(diff_cov_repo.working_dir, "app.py"),
        "--display-verdicts",
        "--max-reruns=2",
        "--rerun-strategy=ALL",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])
    result.stdout.fnmatch_lines(["  CoverageIndependence: genuine"])


def test_sffl(mocker, pytester, sffl_repo):
    """
    Test sffl gives correct results.
    """

    mocked_randint = mocker.patch("random.randint")
    mocked_randint.side_effect = [1, 100, 1, 100]
    pytester.runpytest(
        "--max-reruns=1",
        "--rerun-strategy=ALL",
        "-s",
        "--sffl",
        "--sffl-output-file=sffl_results.csv",
        "--flakefighters",
    )
    expected = pd.DataFrame(
        {
            "file": [os.path.join(sffl_repo.working_dir, "sffl_example.py")] * 5,
            "line": [1, 2, 3, 4, 6],
            "suspiciousness": [1.0, 1.0, 1.0, 0, 0],
        }
    )

    df = pd.read_csv(
        os.path.join(sffl_repo.working_dir, "sffl_results.csv"), index_col=0
    )
    pd.testing.assert_frame_equal(df.round(4), expected.round(4))


def test_gatorgrade_parameterised(pytester, gatorgrade_dir):
    """
    Test that flakefighters can run OK on parameterised tests.
    """
    result = pytester.runpytest(
        os.path.join(gatorgrade_dir, "gatorgrade.py"),
        "--flakefighters",
        "--active-flakefighters",
        "CosineSimilarity",
    )
    result.assert_outcomes(passed=1)
