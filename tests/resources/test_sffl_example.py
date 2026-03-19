from sffl_example import gen_int


def test_1():
    assert "Small" in gen_int()


def test_2():
    assert "number" in gen_int()
