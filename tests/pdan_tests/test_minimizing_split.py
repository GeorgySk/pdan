from collections.abc import Callable
from fractions import Fraction

from gon.base import (
    Contour,
    Polygon,
)
from hypothesis import given

from pdan.pdan import minimizing_split
from tests.strategies.base import metrics
from tests.strategies.geometry import convex_contours_with_area_requirements


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       key=metrics)
def test_area(contour_with_area_requirement: tuple[Contour, Fraction | float],
              key: Callable[[Contour, Contour], Fraction]) -> None:
    contour, area_requirement = contour_with_area_requirement
    key = lambda x, _: x.length
    part, rest = minimizing_split(contour,
                                  area_requirement=area_requirement,
                                  key=key)
    assert Polygon(part).area == area_requirement
    assert Polygon(part).area + Polygon(rest).area == Polygon(contour).area


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       key=metrics)
def test_union(contour_with_area_requirement: tuple[Contour, Fraction | float],
               key: Callable[[Contour, Contour], Fraction]) -> None:
    contour, area_requirement = contour_with_area_requirement
    part, rest = minimizing_split(contour,
                                  area_requirement=area_requirement,
                                  key=key)
    union = Polygon(part) | Polygon(rest)
    assert isinstance(union, Polygon)
    assert union.border == contour
