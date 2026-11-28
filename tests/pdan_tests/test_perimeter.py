from collections.abc import Callable
from fractions import Fraction
from math import hypot

from gon.base import (
    Contour,
    Point,
)
from hypothesis import given

from pdan.pdan import (
    SupportsLessThan,
    minimizing_split,
)
from pdan.radicals import (
    RadicalSum,
    perimeter,
)
from tests.strategies.base import (
    equivalent_metrics,
    positive_nonzero_fractions,
)
from tests.strategies.geometry import (
    convex_contours,
    convex_contours_with_area_requirements,
)

Key = Callable[[Contour, Contour], SupportsLessThan]


@given(convex_contours)
def test_close_to_float_perimeter(contour: Contour) -> None:
    result = perimeter(contour)
    assert isinstance(result, RadicalSum)
    expected = sum(hypot(segment.end.x - segment.start.x,
                         segment.end.y - segment.start.y)
                   for segment in contour.segments)
    assert abs(float(result) - expected) <= 1e-12 * expected


@given(positive_nonzero_fractions)
def test_pythagorean_triangle(scale: Fraction) -> None:
    contour = Contour([Point(0, 0), Point(3 * scale, 0),
                       Point(3 * scale, 4 * scale)])
    assert perimeter(contour) == 12 * scale


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       keys=equivalent_metrics)
def test_same_split_as_length(
        contour_with_area_requirement: tuple[Contour, Fraction | float],
        keys: tuple[Key, Key]) -> None:
    contour, area_requirement = contour_with_area_requirement
    radical_key, length_key = keys
    assert (minimizing_split(contour, area_requirement, key=radical_key)
            == minimizing_split(contour, area_requirement, key=length_key))
