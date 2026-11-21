from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pdan.pdan import (
    ROOT_PRECISION_BITS,
    fourth_root,
)

non_negative_fractions = st.fractions(min_value=0)
negative_fractions = st.fractions(max_value=0).filter(bool)
positive_integers = st.integers(min_value=1)


def ulp(root: Fraction) -> Fraction:
    return Fraction(1, root.denominator)


@given(numerator=st.integers(min_value=0),
       denominator=positive_integers)
def test_exact_on_perfect_fourth_powers(numerator: int,
                                        denominator: int) -> None:
    root = Fraction(numerator, denominator)
    assert fourth_root(root ** 4) == root


@given(non_negative_fractions)
def test_bounds(fraction: Fraction) -> None:
    root = fourth_root(fraction)
    assert root ** 4 <= fraction < (root + ulp(root)) ** 4


@given(non_negative_fractions.filter(bool))
def test_relative_precision(fraction: Fraction) -> None:
    lower_factor = 1 - Fraction(1, 2 ** (ROOT_PRECISION_BITS - 1))
    assert fraction < (fourth_root(fraction) / lower_factor) ** 4


@given(negative_fractions)
def test_negative(fraction: Fraction) -> None:
    with pytest.raises(ValueError, match="negative"):
        fourth_root(fraction)
