from fractions import Fraction

from gon.base import Contour
from hypothesis import strategies as st

from tests.config import (
    MAX_COORDINATE,
    MAX_DENOMINATOR,
    MAX_REQUIREMENTS_COUNT,
    MIN_COORDINATE,
)

MIN_AREA_FRACTION = 0
MAX_AREA_FRACTION = 1


def is_greater_than_zero(value: Fraction) -> bool:
    return value > 0


def is_less_than_zero(value: Fraction) -> bool:
    return value < 0


def is_in_open_unit_interval(value: Fraction) -> bool:
    return 0 < value < 1


fractions = st.fractions(MIN_COORDINATE,
                         MAX_COORDINATE,
                         max_denominator=MAX_DENOMINATOR)
positive_nonzero_fractions = st.fractions(MIN_AREA_FRACTION,
                                          MAX_COORDINATE,
                                          max_denominator=MAX_DENOMINATOR
                                          ).filter(is_greater_than_zero)
unit_fractions = st.fractions(MIN_AREA_FRACTION,
                              MAX_AREA_FRACTION,
                              max_denominator=MAX_DENOMINATOR)
open_interval_unit_fractions = unit_fractions.filter(is_in_open_unit_interval)
negative_fractions = st.fractions(-MAX_AREA_FRACTION,
                                  0,
                                  max_denominator=MAX_DENOMINATOR
                                  ).filter(is_less_than_zero)
integers = st.integers(MIN_COORDINATE, MAX_COORDINATE)
floats = fractions.map(float)
coordinates = fractions | integers | floats
metrics = st.sampled_from([lambda x, _: x.length,
                           lambda x, y: x.length + y.length,
                           lambda x, y: x.length * y.length])


def squared_perimeter_sum(contour: Contour) -> Fraction:
    return sum(((segment.start.x - segment.end.x) ** 2
                + (segment.start.y - segment.end.y) ** 2
                for segment in contour.segments),
               start=Fraction(0))


def float_key(right: Contour, _left: Contour) -> float:
    return float(squared_perimeter_sum(right))


def int_key(right: Contour, _left: Contour) -> int:
    return len(right.vertices)


def tuple_key(right: Contour, _left: Contour) -> tuple[int, float]:
    return len(right.vertices), float(squared_perimeter_sum(right))


non_fraction_metrics = st.sampled_from([float_key, int_key, tuple_key])


def normalize(requirements: list[Fraction]) -> list[Fraction]:
    sum_ = sum(requirements)
    return [requirement / sum_ for requirement in requirements]


fraction_requirements = st.lists(positive_nonzero_fractions,
                                 min_size=2,
                                 max_size=MAX_REQUIREMENTS_COUNT
                                 ).map(normalize)
