"""
Exact sums of square roots of rationals for use in `key` functions.

Exact perimeters of contours are sums of square roots of rationals.
`Contour.length` represents them with `symba` expressions, which get
too slow to compare as the coordinates grow with every cut of a
decomposition. `RadicalSum` compares such sums lazily: it bounds them
with integer arithmetic at increasing precision, and only if the bounds
don't settle the comparison it determines the sign exactly.
"""

from __future__ import annotations

from fractions import Fraction
from math import isqrt, prod
from typing import TYPE_CHECKING, TypeAlias

from gon.base import Contour

if TYPE_CHECKING:
    from collections.abc import Iterable

Atoms = frozenset[int]
"""
Square-free parts of the radicands whose square roots form a term.

Every atom is an integer greater than one without small square
factors, and the term stands for the product of their square roots.
The empty set stands for one. For example, `frozenset({2, 3})` stands
for `sqrt(2) * sqrt(3)`, and `frozenset({6})` for `sqrt(6)`.
"""

Terms = dict[Atoms, Fraction]
"""
Nonzero coefficients of a `RadicalSum` by the atoms of their terms.

For example, `{frozenset(): Fraction(1), frozenset({2}): Fraction(3)}`
stands for `1 + 3 * sqrt(2)`.
"""

Operand: TypeAlias = "RadicalSum | Fraction | int | float"
"""Numbers that `RadicalSum` supports as operands."""

SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)
"""Primes whose squares `RadicalSum.sqrt` removes from radicands."""

INITIAL_PRECISION_BITS = 64
"""Number of fractional bits of the first bounds of a `RadicalSum`."""

MAX_FILTER_PRECISION_BITS = 1 << 14
"""
Number of fractional bits beyond which bounds give up on the sign.

Above it, `sign` determines the sign exactly instead, which is
reached only for sums that are zero or extremely close to it.
"""

FLOAT_MANTISSA_BITS = 64
"""Number of significant bits of the bounds that `float` converts."""


class RadicalSum:
    """
    Represents an exact sum of products of square roots of rationals.

    Supports addition, subtraction and multiplication with other sums,
    integers, fractions and floats (converted exactly), as well as exact
    comparisons with them. Comparisons first bound both sides with
    integer arithmetic and only fall back to exact computations if the
    bounds overlap, which happens mostly when the values are equal.

    Instances are not hashable, since equal values may have different
    representations, for example `sqrt(2) * sqrt(3)` and `sqrt(6)`.

    >>> root_2, root_3 = RadicalSum.sqrt(2), RadicalSum.sqrt(3)
    >>> root_2 * root_3
    Fraction(1, 1)*sqrt(2)*sqrt(3)
    >>> root_2 * root_3 == RadicalSum.sqrt(6)
    True
    >>> root_2 < Fraction(99, 70)
    True
    >>> root_2 + root_3 > 3.14
    True
    >>> float(root_2)
    1.4142135623730951
    """

    __slots__ = ("_terms",)

    _terms: Terms

    def __init__(self, value: Fraction | int = 0) -> None:
        """
        Creates a sum equal to the given rational number.

        :param value: rational number to represent
        """
        fraction = Fraction(value)
        self._terms = {frozenset(): fraction} if fraction else {}

    @classmethod
    def sqrt(cls, value: Fraction | int) -> RadicalSum:
        """
        Returns exact square root of a non-negative rational number.

        Represents the root of `a / b` as the root of `a * b` divided
        by `b`, and moves perfect squares and the squares of small primes
        out of the root, so that equal roots usually share one term.

        >>> RadicalSum.sqrt(8)
        Fraction(2, 1)*sqrt(2)
        >>> RadicalSum.sqrt(Fraction(1, 2))
        Fraction(1, 2)*sqrt(2)
        >>> RadicalSum.sqrt(9)
        Fraction(3, 1)

        :param value: non-negative rational number
        :return: sum equal to the square root of `value`.
        :raises ValueError: if `value` is negative.
        """
        fraction = Fraction(value)
        if fraction < 0:
            raise ValueError("Cannot take square root of negative number: "
                             f"{fraction}.")
        radicand = fraction.numerator * fraction.denominator
        factor, atom = split_square_factor(radicand)
        coefficient = Fraction(factor, fraction.denominator)
        return cls._from_terms({} if atom == 0
                               else {frozenset()
                                     if atom == 1
                                     else frozenset([atom]): coefficient})

    @classmethod
    def _from_terms(cls, terms: Terms) -> RadicalSum:
        """
        Creates a sum from its terms without copying them.

        :param terms: nonzero coefficients by the atoms of their terms
        :return: sum of the terms.
        """
        result = cls.__new__(cls)
        result._terms = terms  # noqa: SLF001
        return result

    def __repr__(self) -> str:
        """
        Returns a representation of the sum as an expression.

        :return: terms joined with `+`, each a coefficient times
            the square roots of its atoms.
        """
        if not self._terms:
            return f"{type(self).__name__}(0)"
        return " + ".join(
            "*".join([repr(coefficient),
                      *(f"sqrt({atom})" for atom in sorted(atoms))])
            for atoms, coefficient in sorted(self._terms.items(),
                                             key=lambda item: sorted(item[0])))

    def __float__(self) -> float:
        """
        Returns the closest float to the sum, up to rounding of bounds.

        :return: float within a relative error of about
            `2 ** -FLOAT_MANTISSA_BITS` of the sum.
        """
        terms = self._terms
        if sign(terms) == 0:
            return 0.0
        precision = INITIAL_PRECISION_BITS
        while True:
            lower, upper = to_bounds(terms, precision)
            if min(abs(lower), abs(upper)) >> FLOAT_MANTISSA_BITS >= (
                    upper - lower):
                return float(Fraction(lower + upper, 2 << precision))
            precision *= 2

    def __bool__(self) -> bool:
        """
        Checks if the sum is nonzero.

        :return: whether the sum is not equal to zero.
        """
        return sign(self._terms) != 0

    def __pos__(self) -> RadicalSum:
        """
        Returns the sum itself.

        :return: the same sum.
        """
        return self

    def __neg__(self) -> RadicalSum:
        """
        Returns the sum with the opposite sign.

        :return: sum with all coefficients negated.
        """
        return self._from_terms({atoms: -coefficient
                                 for atoms, coefficient
                                 in self._terms.items()})

    def __add__(self, other: Operand) -> RadicalSum:
        """
        Adds a number to the sum.

        :param other: sum or rational number to add
        :return: sum of both.
        """
        other_sum = to_radical_sum(other)
        if other_sum is None:
            return NotImplemented
        return self._from_terms(add_terms(self._terms, other_sum._terms))

    __radd__ = __add__

    def __sub__(self, other: Operand) -> RadicalSum:
        """
        Subtracts a number from the sum.

        :param other: sum or rational number to subtract
        :return: difference of both.
        """
        other_sum = to_radical_sum(other)
        if other_sum is None:
            return NotImplemented
        return self._from_terms(add_terms(self._terms,
                                          (-other_sum)._terms))

    def __rsub__(self, other: Operand) -> RadicalSum:
        """
        Subtracts the sum from a number.

        :param other: sum or rational number to subtract from
        :return: difference of both.
        """
        other_sum = to_radical_sum(other)
        if other_sum is None:
            return NotImplemented
        return other_sum - self

    def __mul__(self, other: Operand) -> RadicalSum:
        """
        Multiplies the sum by a number.

        :param other: sum or rational number to multiply by
        :return: product of both.
        """
        other_sum = to_radical_sum(other)
        if other_sum is None:
            return NotImplemented
        return self._from_terms(multiply_terms(self._terms,
                                               other_sum._terms))

    __rmul__ = __mul__

    def __eq__(self, other: object) -> bool:
        """
        Checks if the sum equals a number exactly.

        :param other: sum or rational number to compare with
        :return: whether both are equal.
        """
        if not isinstance(other, RadicalSum | Fraction | int | float):
            return NotImplemented
        return self._compare(other) == 0

    __hash__ = None  # type: ignore[assignment]

    def __lt__(self, other: Operand) -> bool:
        """
        Checks if the sum is less than a number.

        :param other: sum or rational number to compare with
        :return: whether the sum is less than `other`.
        """
        return self._compare(other) < 0

    def __le__(self, other: Operand) -> bool:
        """
        Checks if the sum is less than or equal to a number.

        :param other: sum or rational number to compare with
        :return: whether the sum is not greater than `other`.
        """
        return self._compare(other) <= 0

    def __gt__(self, other: Operand) -> bool:
        """
        Checks if the sum is greater than a number.

        :param other: sum or rational number to compare with
        :return: whether the sum is greater than `other`.
        """
        return self._compare(other) > 0

    def __ge__(self, other: Operand) -> bool:
        """
        Checks if the sum is greater than or equal to a number.

        :param other: sum or rational number to compare with
        :return: whether the sum is not less than `other`.
        """
        return self._compare(other) >= 0

    def _compare(self, other: Operand) -> int:
        """
        Returns the sign of the difference between the sum and a number.

        :param other: sum or rational number to compare with
        :return: -1, 0 or 1 if the sum is less than, equal to or greater
            than `other`, respectively.
        :raises TypeError: if `other` is not a number.
        """
        other_sum = to_radical_sum(other)
        if other_sum is None:
            raise TypeError(f"Cannot compare {type(self).__name__} "
                            f"with {type(other).__name__}.")
        return sign(add_terms(self._terms, (-other_sum)._terms))  # noqa: SLF001


def perimeter(contour: Contour) -> RadicalSum:
    """
    Returns exact perimeter of the contour.

    Equals `Contour.length`, but compares much faster as the sizes
    of the coordinates grow, so it suits `key` functions
    of `minimizing_decomposition` with exact areas.

    >>> from gon.base import Point
    >>> perimeter(Contour([Point(0, 0), Point(3, 0), Point(0, 4)]))
    Fraction(12, 1)
    >>> perimeter(Contour([Point(0, 0), Point(1, 0), Point(0, 1)]))
    Fraction(2, 1) + Fraction(1, 1)*sqrt(2)

    :param contour: contour with integer, fraction or float coordinates
    :return: sum of the lengths of the contour's edges.
    """
    vertices = contour.vertices
    return sum_radicals(
        RadicalSum.sqrt((Fraction(end.x) - Fraction(start.x)) ** 2
                        + (Fraction(end.y) - Fraction(start.y)) ** 2)
        for start, end in zip(vertices, [*vertices[1:], vertices[0]]))


def sum_radicals(values: Iterable[RadicalSum]) -> RadicalSum:
    """
    Adds up sums without creating intermediate ones.

    :param values: sums to add up
    :return: sum of all of them; zero if there are none.
    """
    terms: Terms = {}
    for value in values:
        terms = add_terms(terms, value._terms)  # noqa: SLF001
    return RadicalSum._from_terms(terms)  # noqa: SLF001


def to_radical_sum(value: object) -> RadicalSum | None:
    """
    Converts a number to a sum if possible.

    Floats are converted to the exact binary value they store.

    :param value: sum, integer, fraction or float
    :return: equal sum, or `None` if `value` is not a supported number.
    """
    if isinstance(value, RadicalSum):
        return value
    if isinstance(value, Fraction | int):
        return RadicalSum(value)
    if isinstance(value, float):
        return RadicalSum(Fraction(value))
    return None


def split_square_factor(value: int) -> tuple[int, int]:
    """
    Splits a non-negative integer into a square and the rest.

    Moves the squares of `SMALL_PRIMES` out of the integer, and then
    the rest of it entirely if it is a perfect square. The remaining
    part may still have large square factors.

    >>> split_square_factor(72)  # 6 ** 2 * 2
    (6, 2)
    >>> split_square_factor(53 ** 2)  # perfect square
    (53, 1)
    >>> split_square_factor(53 ** 2 * 3)  # 53 is not in SMALL_PRIMES
    (1, 8427)

    :param value: non-negative integer
    :return: integer `factor` and integer `rest` such that
        `factor ** 2 * rest == value`, with `rest` either zero, one,
        or not a perfect square.
    """
    if value == 0:
        return 0, 0
    factor = 1
    for prime in SMALL_PRIMES:
        square = prime * prime
        while value % square == 0:
            value //= square
            factor *= prime
    root = isqrt(value)
    if root * root == value:
        return factor * root, 1
    return factor, value


def add_terms(first: Terms, second: Terms) -> Terms:
    """
    Adds two sums given by their terms.

    :param first: terms of the first sum
    :param second: terms of the second sum
    :return: terms of the sum of both, without zero coefficients.
    """
    result = dict(first)
    for atoms, coefficient in second.items():
        total = result.get(atoms, 0) + coefficient
        if total:
            result[atoms] = total
        else:
            result.pop(atoms, None)
    return result


def multiply_terms(first: Terms, second: Terms) -> Terms:
    """
    Multiplies two sums given by their terms.

    The square root of an atom appearing in both terms of a product
    squares to the atom itself, which goes to the coefficient.
    For example, `(sqrt(2) + sqrt(3)) * sqrt(2)` is `2 + sqrt(2 * 3)`:

    >>> multiply_terms({frozenset({2}): Fraction(1),
    ...                 frozenset({3}): Fraction(1)},
    ...                {frozenset({2}): Fraction(1)})
    {frozenset(): Fraction(2, 1), frozenset({2, 3}): Fraction(1, 1)}

    :param first: terms of the first sum
    :param second: terms of the second sum
    :return: terms of the product of both, without zero coefficients.
    """
    result: Terms = {}
    for first_atoms, first_coefficient in first.items():
        for second_atoms, second_coefficient in second.items():
            common = first_atoms & second_atoms
            atoms = first_atoms ^ second_atoms
            total = (result.get(atoms, 0)
                     + first_coefficient * second_coefficient
                     * prod(common))
            if total:
                result[atoms] = total
            else:
                result.pop(atoms, None)
    return result


def sign(terms: Terms) -> int:
    """
    Determines the sign of a sum exactly.

    Tries `filtered_sign` first, and falls back to `exact_sign`
    only if the bounds don't exclude zero.

    :param terms: terms of the sum
    :return: -1, 0 or 1 if the sum is negative, zero or positive,
        respectively.
    """
    if not terms:
        return 0
    if len(terms) == 1:
        (coefficient,) = terms.values()
        return 1 if coefficient > 0 else -1
    result = filtered_sign(terms)
    return exact_sign(terms) if result is None else result


def filtered_sign(terms: Terms) -> int | None:
    """
    Determines the sign of a sum from its bounds if possible.

    Doubles the precision of the bounds from `INITIAL_PRECISION_BITS`
    until they exclude zero or the precision exceeds
    `MAX_FILTER_PRECISION_BITS`.

    :param terms: terms of the sum
    :return: -1 or 1 if the sum is negative or positive, respectively;
        `None` if the bounds don't settle it.

    For example, `sqrt(2) * sqrt(3) - sqrt(6)` is zero, so no bounds
    exclude zero, while `sqrt(2) + sqrt(3) - sqrt(10)` is negative:

    >>> root_6 = RadicalSum.sqrt(6)
    >>> print(filtered_sign((RadicalSum.sqrt(2) * RadicalSum.sqrt(3)
    ...                      - root_6)._terms))
    None
    >>> filtered_sign((RadicalSum.sqrt(2) + RadicalSum.sqrt(3)
    ...                - RadicalSum.sqrt(10))._terms)
    -1
    """
    precision = INITIAL_PRECISION_BITS
    while precision <= MAX_FILTER_PRECISION_BITS:
        lower, upper = to_bounds(terms, precision)
        if lower > 0:
            return 1
        if upper < 0:
            return -1
        precision *= 2
    return None


def to_bounds(terms: Terms, precision: int) -> tuple[int, int]:
    """
    Bounds a sum by multiples of `2 ** -precision`.

    For a term `n / d * sqrt(a)` the value scaled by `2 ** precision`
    is the square root of `n ** 2 * a * 4 ** precision / d ** 2`,
    and its floor equals the integer square root of the floor
    of that fraction, so each term is bounded by consecutive integers.
    For example, with 4 fractional bits `sqrt(2)` (about 1.414) lies
    between `22 / 16` and `23 / 16`, and `sqrt(2) - 1` between `5 / 16`
    and `7 / 16`, since every term widens the bounds by one:

    >>> to_bounds({frozenset({2}): Fraction(1)}, 4)
    (22, 23)
    >>> to_bounds({frozenset({2}): Fraction(1),
    ...            frozenset(): Fraction(-1)}, 4)
    (5, 7)

    :param terms: terms of the sum
    :param precision: number of fractional bits of the bounds
    :return: integers `lower` and `upper` such that the sum lies
        between `lower * 2 ** -precision` and `upper * 2 ** -precision`.
    """
    lower = upper = 0
    for atoms, coefficient in terms.items():
        numerator, denominator = (coefficient.numerator,
                                  coefficient.denominator)
        scaled = isqrt((numerator * numerator * prod(atoms) << 2 * precision)
                       // (denominator * denominator))
        if numerator > 0:
            lower += scaled
            upper += scaled + 1
        else:
            lower -= scaled + 1
            upper -= scaled
    return lower, upper


def exact_sign(terms: Terms) -> int:
    """
    Determines the sign of a sum with exact arithmetic.

    Picks an atom `r` of the sum and writes the sum as `P + Q * sqrt(r)`,
    where `P` and `Q` don't depend on `r`. If `P` and `Q` have the same
    sign, or one of them is zero, the sign follows directly. Otherwise
    it is the sign of `P` times the sign of `P ** 2 - r * Q ** 2`.
    All three sums have fewer atoms than the original one, so the
    recursion ends.

    For example, `sqrt(2) * sqrt(3) - sqrt(6)` with `r = 2` gives
    `P = -sqrt(6)` and `Q = sqrt(3)` of opposite signs, and
    `P ** 2 - 2 * Q ** 2 = 6 - 6` is zero, so the sum is zero:

    >>> exact_sign({frozenset({2, 3}): Fraction(1),
    ...             frozenset({6}): Fraction(-1)})
    0

    :param terms: terms of the sum, with at least one atom
    :return: -1, 0 or 1 if the sum is negative, zero or positive,
        respectively.
    """
    atom = min(atom for atoms in terms for atom in atoms)
    rest: Terms = {}
    factor: Terms = {}
    for atoms, coefficient in terms.items():
        if atom in atoms:
            factor[atoms - {atom}] = coefficient
        else:
            rest[atoms] = coefficient
    rest_sign = sign(rest)
    factor_sign = sign(factor)
    if factor_sign in {0, rest_sign}:
        return rest_sign
    if rest_sign == 0:
        return factor_sign
    difference = add_terms(
        multiply_terms(rest, rest),
        multiply_terms(multiply_terms(factor, factor),
                       {frozenset(): Fraction(-atom)}))
    return rest_sign * sign(difference)
