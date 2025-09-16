"""
Test DeFlaker algorithm.
"""

import os


def test_files_exist(triangle_repo, deflaker_repo):
    """
    Test that the necessary fixture files have actually heen created.
    """
    assert os.path.exists(
        os.path.join(triangle_repo, "triangle.py")
    ), f"Fixture file {os.path.join(triangle_repo, 'triangle.py')} not present."
    assert os.path.exists(
        os.path.join(deflaker_repo, "app.py")
    ), f"Fixture file {os.path.join(deflaker_repo, 'app.py')} not present."


def test_real_failures(pytester, triangle_repo):
    """Make sure that pytest accepts our fixture."""

    # run pytest with the following cmd args
    result = pytester.runpytest(os.path.join(triangle_repo, "triangle.py"), f"--repo={triangle_repo}")

    print(result.readouterr())

    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(
        [
            f"FAILED {os.path.join('..','triangle_repo0', 'triangle.py')}::test_eqiulateral*",
            f"FAILED {os.path.join('..','triangle_repo0', 'triangle.py')}::test_isosceles*",
            f"FAILED {os.path.join('..','triangle_repo0', 'triangle.py')}::test_scalene*",
        ]
    )


# def test_deflaker_example(pytester, deflaker_repo):
#     """Make sure that pytest accepts our fixture."""
#
#     # run pytest with the following cmd args
#     result = pytester.runpytest(
#         os.path.join(deflaker_repo, "app.py"),
#         f"--repo={deflaker_repo}",
#     )
#
#     assert result.ret == 1, "Expected tests to fail"
#
#     result.stdout.fnmatch_lines(["Real faults ['deflaker_repo0/app.py::test_app']"])
