from collections.abc import Callable
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pdan.pdan import (
    ROOT_PRECISION_BITS,
    fourth_root,
    robust_sqrt,
)

non_negative_fractions = st.fractions(min_value=0)
negative_fractions = st.fractions(max_value=0).filter(bool)
roots = st.sampled_from([robust_sqrt, fourth_root])
positive_integers = st.integers(min_value=1)


def ulp(root: Fraction) -> Fraction:
    return Fraction(1, root.denominator)


@given(numerator=st.integers(min_value=0),
       denominator=positive_integers)
def test_sqrt_exact_on_perfect_squares(numerator: int,
                                       denominator: int) -> None:
    root = Fraction(numerator, denominator)
    assert robust_sqrt(root ** 2) == root


@given(numerator=st.integers(min_value=0),
       denominator=positive_integers)
def test_fourth_root_exact_on_perfect_fourth_powers(numerator: int,
                                                    denominator: int) -> None:
    root = Fraction(numerator, denominator)
    assert fourth_root(root ** 4) == root


@given(non_negative_fractions)
def test_sqrt_bounds(fraction: Fraction) -> None:
    root = robust_sqrt(fraction)
    assert root ** 2 <= fraction < (root + ulp(root)) ** 2


@given(non_negative_fractions)
def test_fourth_root_bounds(fraction: Fraction) -> None:
    root = fourth_root(fraction)
    assert root ** 4 <= fraction < (root + ulp(root)) ** 4


@given(non_negative_fractions.filter(bool))
def test_relative_precision(fraction: Fraction) -> None:
    lower_factor = 1 - Fraction(1, 2 ** (ROOT_PRECISION_BITS - 1))
    assert fraction < (robust_sqrt(fraction) / lower_factor) ** 2
    assert fraction < (fourth_root(fraction) / lower_factor) ** 4


@given(fraction=negative_fractions,
       root=roots)
def test_negative(fraction: Fraction,
                  root: Callable[[Fraction], Fraction]) -> None:
    with pytest.raises(ValueError, match="negative"):
        root(fraction)
