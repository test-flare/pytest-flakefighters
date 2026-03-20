import random

from sffl_example import gen_int


# Flaky
def test_1():
    assert "Small" in gen_int(random)


# Stable
def test_2():
    assert "number" in gen_int(random)
