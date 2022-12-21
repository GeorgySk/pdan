from fractions import Fraction
from typing import List

from hypothesis import strategies as st

from tests.config import (MAX_COORDINATE,
                          MAX_DENOMINATOR,
                          MAX_REQUIREMENTS_COUNT,
                          MIN_COORDINATE)

MIN_AREA_FRACTION = 0
MAX_AREA_FRACTION = 1


def is_greater_than_zero(value: Fraction) -> bool:
    return value > 0


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
metrics = st.sampled_from([lambda x, y: x.length,
                           lambda x, y: x.length + y.length,
                           lambda x, y: x.length * y.length])


def normalize(requirements: List[Fraction]) -> List[Fraction]:
    sum_ = sum(requirements)
    return [requirement / sum_ for requirement in requirements]


fraction_requirements = st.lists(positive_nonzero_fractions,
                                 min_size=2,
                                 max_size=MAX_REQUIREMENTS_COUNT
                                 ).map(normalize)
