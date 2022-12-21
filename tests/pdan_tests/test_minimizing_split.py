from fractions import Fraction
from numbers import Real
from typing import Callable

from gon.base import Contour
from gon.base import Polygon
from hypothesis import (example,
                        given,
                        settings)

from pdan.pdan import minimizing_split
from tests.strategies.base import (metrics,
                                   open_interval_unit_fractions)
from tests.strategies.geometry import convex_contours


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions,
       key=metrics)
def test_area(contour: Contour,
              unit_fraction: Real,
              key: Callable[[Contour, Contour], Fraction]) -> None:
    area_requirement = unit_fraction * Polygon(contour).area
    key = lambda x, y: x.length
    part, rest = minimizing_split(contour,
                                  area_requirement=area_requirement,
                                  key=key)
    assert Polygon(part).area == area_requirement
    assert Polygon(part).area + Polygon(rest).area == Polygon(contour).area


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions,
       key=metrics)
def test_union(contour: Contour,
               unit_fraction: Real,
               key: Callable[[Contour, Contour], Fraction]) -> None:
    area_requirement = unit_fraction * Polygon(contour).area
    part, rest = minimizing_split(contour,
                                  area_requirement=area_requirement,
                                  key=key)
    union = Polygon(part) | Polygon(rest)
    assert isinstance(union, Polygon)
    assert union.border == contour
