"""
Test DeFlaker algorithm.
"""

import os


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
