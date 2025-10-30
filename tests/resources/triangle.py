import os

import pytest

SUFFIX = ""
if os.path.exists("suffix.txt"):
    with open("suffix.txt") as f:
        SUFFIX = f.readline().strip()


def triangle_type(a, b, c):
    if a + b <= c or b + c <= a or c + a <= b:
        return "Invalid" + SUFFIX
    if a == b and b == c:
        return "Equilateral" + SUFFIX
    if a == b or a == c or b == c:
        return "Isosceles" + SUFFIX
    return "Scalene" + SUFFIX


def test_eqiulateral():
    assert triangle_type(1, 1, 1) == "Equilateral"


def test_isosceles():
    assert triangle_type(1, 2, 2) == "Isosceles"


@pytest.mark.skip(reason="Need to test a skipped test")
def test_scalene():
    assert triangle_type(2, 3, 4) == "Scalene"
