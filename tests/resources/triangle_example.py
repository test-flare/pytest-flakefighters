def triangle_type(a, b, c):
    if a + b <= c or b + c <= a or c + a <= b:
        return "Invalid"
    if a == b and b == c:
        return "Equilateral"
    if a == b or a == c or b == c:
        return "Isosceles"
    return "Scalene"


def test_eqiulateral():
    assert triangle_type(1, 1, 1) == "Equilateral"


def test_isosceles():
    assert triangle_type(1, 2, 2) == "Isosceles"


def test_scalene():
    assert triangle_type(2, 3, 4) == "Scalene"
