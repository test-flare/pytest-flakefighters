"""
This module implements tests for function-level coverage.
"""

import os
import sys

from pytest_flakefighters.function_coverage import Profiler


def test_function_coverage(flaky_triangle_repo):
    """
    Test function definition scraping.
    """
    profiler = Profiler()
    assert not profiler.function_defs, f"Expected empty but got {profiler.function_defs}"

    profiler.update_function_defs(os.path.join(flaky_triangle_repo.working_dir, "triangle.py"))
    expected = {
        "triangle_type": list(range(11, 19)),
        "test_eqiulateral": list(range(21, 23)),
        "test_isosceles": list(range(25, 27)),
        "test_scalene": list(range(30, 32)),
    }
    function_defs = profiler.function_defs.get(os.path.join(flaky_triangle_repo.working_dir, "triangle.py"))
    assert function_defs == expected, f"Expected {expected} but got {function_defs}."


def test_profile_fun_calls():
    """Make sure that function-level coverage runs fine."""
    profiler = Profiler()
    assert not profiler.function_defs, f"Expected empty but got {profiler.function_defs}"
    sys.path.append("tests")
    from resources.triangle import triangle_type  # pylint: disable=C0415

    sys.setprofile(profiler.profile_fun_calls)
    triangle_type(3, 4, 5)
    sys.setprofile(None)

    expected = {
        "triangle_type": list(range(11, 19)),
        "test_eqiulateral": list(range(21, 23)),
        "test_isosceles": list(range(25, 27)),
        "test_scalene": list(range(30, 32)),
    }
    triangle = os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", "triangle.py")
    function_defs = profiler.function_defs.get(triangle)
    assert function_defs == expected, f"Expected {expected} but got {function_defs}."
    assert profiler.coverage_data.lines(triangle) == list(range(11, 19))
