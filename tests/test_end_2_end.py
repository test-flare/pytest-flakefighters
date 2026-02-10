"""
Test DeFlaker algorithm.
"""

import json
import os

from pytest import ExitCode


def test_flakefighters(pytester, deflaker_repo):
    """
    Test that flakefighters is registered when the --flakefighters argument is passed.
    """
    reprec = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "--flakefighters",
        "-s",
        "--flakefighters",
    ).reprec
    assert any(
        call.plugin_name == "flakefighters" for call in reprec.getcalls("pytest_plugin_registered")
    ), "Flakefighters should be registered when --no-flakefighters is not passed"


def test_no_flakefighters(pytester, deflaker_repo):
    """
    Test that flakefighters is not registered when the --flakefighters argument is not passed.
    """
    reprec = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "-s",
        "--flakefighters",
    ).reprec
    assert any(
        call.plugin_name == "flakefighters" for call in reprec.getcalls("pytest_plugin_registered")
    ), "Flakefighters should not be registered when --no-flakefighters is passed"


def test_real_failures(pytester, deflaker_repo):
    """Make sure that genuine failures are labelled as such."""

    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "-s",
        "--flakefighters",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "FAILED app.py::test_app*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."


def test_real_failures_non_py_file_changed(pytester, deflaker_repo):
    """Make sure that genuine failures are labelled as such."""

    # Create a spurious text file to make sure that this doesn't cause errors
    # e.g. when trying to parse source files
    with open(os.path.join(deflaker_repo.working_dir, "test.txt"), "w") as f:
        f.write("Hello world")

    deflaker_repo.index.add(["test.txt"])
    deflaker_repo.index.commit("Added a new text file.")

    with open(os.path.join(deflaker_repo.working_dir, "test.txt"), "a") as f:
        f.write("Hello world!")

    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "-s",
        "--flakefighters",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "FLAKY app.py::test_app*",
        ]
    )
    assert result.ret == ExitCode.TESTS_FAILED, f"Expected exit code {ExitCode.TESTS_FAILED} but was {result.ret}."


def test_rerun_flaky_failures(pytester, flaky_reruns_repo):
    """Test exit code is OK when only flaky failures"""

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--flakefighters",
        "--max-reruns=3",
    )

    result.assert_outcomes(passed=1)
    assert result.ret == ExitCode.OK, f"Expected exit code {ExitCode.OK} but was {result.ret}."


def test_suppress_flaky_failures(pytester, flaky_reruns_repo):
    """Test exit code is OK when only flaky failures"""

    result = pytester.runpytest(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "-s",
        "--flakefighters",
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
        "--flakefighters",
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
        "--flakefighters",
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
        "--flakefighters",
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
        "--flakefighters",
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FLAKY app.py::test_app - assert False"])


def test_html_report(pytester, deflaker_repo):
    """
    Test that an html report is produced.
    """

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "--html=report.html",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])

    assert os.path.exists(
        os.path.join(deflaker_repo.working_dir, "report.html")
    ), "Expected report.html to exist but it did not."

    # Test that the DeFlaker result is in the file and reports a genuine fault
    with open(os.path.join(deflaker_repo.working_dir, "report.html")) as f:
        assert any("&lt;li&gt;&lt;strong&gt;DeFlaker:&lt;/strong&gt; genuine&lt;" in line for line in f)


def test_xml_report(pytester, deflaker_repo):
    """
    Test that an xml report is produced.
    """

    with open(os.path.join(deflaker_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.coverage_independence.CoverageIndependence]\n"
        )
        f.write("run_live=true\n")
        f.write("[tool.pytest.ini_options.pytest_flakefighters.flakefighters.deflaker.DeFlaker]\n")
        f.write("run_live=true\n")

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "--junitxml=report.xml",
        "--max-reruns=2",
        "--rerun-strategy=ALL",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])

    assert os.path.exists(
        os.path.join(deflaker_repo.working_dir, "report.xml")
    ), "Expected report.xml to exist but it did not."

    # Test that the DeFlaker result is in the file and reports a genuine fault
    with open(os.path.join(deflaker_repo.working_dir, "report.xml")) as f:
        assert any("<DeFlaker>genuine</DeFlaker>" in line for line in f)
    with open(os.path.join(deflaker_repo.working_dir, "report.xml")) as f:
        assert any("<CoverageIndependence>genuine</CoverageIndependence>" in line for line in f)


def test_json_report(pytester, deflaker_repo):
    """
    Test that an json report is produced.
    """

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "--json-report",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])

    assert os.path.exists(
        os.path.join(deflaker_repo.working_dir, ".report.json")
    ), "Expected .report.json to exist but it did not."

    with open(os.path.join(deflaker_repo.working_dir, ".report.json")) as f:
        tests = json.load(f)["tests"]
        assert len(tests) == 1, f"Expected only one test but found {len(tests)}"
        assert tests[0]["call"]["metadata"]["executions"][0]["flakefighter_results"] == {
            "DeFlaker": "genuine",
        }


def test_display_verdicts(pytester, deflaker_repo):
    """
    Test that outcomes are displayed to terminal.
    """

    # run pytest with the following cmd args
    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "--display-verdicts",
        "-s",
        "--flakefighters",
    )

    # Test original functionality is unchanged
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["FAILED app.py::test_app - assert False"])
    result.stdout.fnmatch_lines(["  DeFlaker: genuine"])


def test_display_test_level_verdicts(pytester, deflaker_repo):
    """
    Test that outcomes are displayed to terminal.
    """

    with open(os.path.join(deflaker_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.coverage_independence.CoverageIndependence]\n"
        )
        f.write("run_live=true\n")
        f.write("[tool.pytest.ini_options.pytest_flakefighters.flakefighters.deflaker.DeFlaker]\n")
        f.write("run_live=true\n")

    result = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
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
