from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pdan.radicals import (
    RadicalSum,
    split_square_factor,
)

non_negative_fractions = st.fractions(min_value=0, max_denominator=10 ** 6)
small_fractions = st.fractions(-10 ** 6, 10 ** 6, max_denominator=10 ** 6)
negative_fractions = st.fractions(max_value=0).filter(bool)
roots = non_negative_fractions.map(RadicalSum.sqrt)
coefficients = small_fractions.filter(bool)
radical_sums = st.lists(st.tuples(coefficients, non_negative_fractions),
                        max_size=5).map(
    lambda pairs: sum((coefficient * RadicalSum.sqrt(radicand)
                       for coefficient, radicand in pairs),
                      start=RadicalSum()))


@given(non_negative_fractions)
def test_sqrt_of_square(fraction: Fraction) -> None:
    assert RadicalSum.sqrt(fraction * fraction) == fraction


@given(non_negative_fractions)
def test_sqrt_squared(fraction: Fraction) -> None:
    root = RadicalSum.sqrt(fraction)
    assert root * root == fraction


@given(negative_fractions)
def test_sqrt_of_negative(fraction: Fraction) -> None:
    with pytest.raises(ValueError, match="negative"):
        RadicalSum.sqrt(fraction)


@given(non_negative_fractions, non_negative_fractions)
def test_product_of_roots(first: Fraction, second: Fraction) -> None:
    # different representations of one value need the exact fallback
    assert (RadicalSum.sqrt(first) * RadicalSum.sqrt(second)
            == RadicalSum.sqrt(first * second))


@given(non_negative_fractions, non_negative_fractions)
def test_square_of_sum(first: Fraction, second: Fraction) -> None:
    total = RadicalSum.sqrt(first) + RadicalSum.sqrt(second)
    assert total * total == (first + second
                             + 2 * RadicalSum.sqrt(first * second))


@given(radical_sums, radical_sums)
def test_trichotomy(first: RadicalSum, second: RadicalSum) -> None:
    assert sum([first < second, first == second, first > second]) == 1
    assert (first <= second) == (not first > second)
    assert (first >= second) == (not first < second)


@given(radical_sums, radical_sums)
def test_comparison_by_difference(first: RadicalSum,
                                  second: RadicalSum) -> None:
    assert (first < second) == (second - first > 0)
    assert (first == second) == (not first - second)


@given(radical_sums)
def test_negation(value: RadicalSum) -> None:
    assert value + -value == 0
    assert (value > 0) == (-value < 0)


@given(radical_sums, radical_sums, radical_sums)
def test_distributivity(first: RadicalSum,
                        second: RadicalSum,
                        third: RadicalSum) -> None:
    assert first * (second + third) == first * second + first * third


@given(radical_sums, radical_sums)
def test_agrees_with_floats(first: RadicalSum, second: RadicalSum) -> None:
    first_float, second_float = float(first), float(second)
    tolerance = 1e-9 * max(abs(first_float), abs(second_float), 1)
    if first_float + tolerance < second_float:
        assert first < second
    elif second_float + tolerance < first_float:
        assert first > second


@given(radical_sums, small_fractions)
def test_mixed_operands(value: RadicalSum, fraction: Fraction) -> None:
    assert value + fraction == fraction + value
    assert value - fraction == -(fraction - value)
    assert value * fraction == fraction * value
    assert (value < fraction) == (value - fraction < 0)
    assert (value == float(fraction)) == (value == Fraction(float(fraction)))


def test_close_but_unequal() -> None:
    # differs from zero far beyond the precision of the first bounds
    value = (RadicalSum.sqrt(2) * RadicalSum.sqrt(3) - RadicalSum.sqrt(6)
             + RadicalSum.sqrt(Fraction(1, 10 ** 200)))
    assert value > 0
    assert float(value) == pytest.approx(1e-100)


def test_unhashable() -> None:
    with pytest.raises(TypeError):
        hash(RadicalSum.sqrt(2))


def test_unsupported_operand() -> None:
    with pytest.raises(TypeError):
        RadicalSum.sqrt(2) < "2"  # type: ignore[operator]  # noqa: B015
    assert RadicalSum.sqrt(2) != "2"


@given(st.integers(min_value=0))
def test_split_square_factor(value: int) -> None:
    factor, rest = split_square_factor(value)
    assert factor * factor * rest == value
