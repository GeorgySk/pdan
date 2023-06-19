from typing import List

from gon.base import Point
from hypothesis import (assume,
                        given)

from pdan.pdan import slope_intercept
from tests.strategies.geometry import (fraction_points,
                                       points_pairs)


@given(points_pairs)
def test_commutativity(points_pair: List[Point]) -> None:
    first, second = points_pair
    assume(first.x != second.x)
    first_slope, first_intercept = slope_intercept(first, second)
    second_slope, second_intercept = slope_intercept(second, first)
    assert first_slope == second_slope
    assert first_intercept == second_intercept


@given(fraction_points)
def test_origin(point: Point) -> None:
    origin = Point(0, 0)
    assume(point.x != origin.x)
    slope, intercept = slope_intercept(origin, point)
    assert intercept == 0
    assert slope == point.y / point.x

