from collections.abc import Callable
from fractions import Fraction

import pytest
from gon.base import (
    EMPTY,
    Contour,
    Polygon,
)
from hypothesis import given

from pdan.pdan import minimizing_split
from tests.strategies.base import (
    metrics,
    negative_fractions,
    positive_nonzero_fractions,
)
from tests.strategies.geometry import (
    convex_contours,
    convex_contours_with_area_requirements,
)


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


@given(contour=convex_contours,
       key=metrics)
def test_zero_requirement(contour: Contour,
                          key: Callable[[Contour, Contour], Fraction]) -> None:
    part, rest = minimizing_split(contour,
                                  area_requirement=0,
                                  key=key)
    assert part is EMPTY
    assert rest == contour


@given(contour=convex_contours,
       key=metrics)
def test_full_requirement(contour: Contour,
                          key: Callable[[Contour, Contour], Fraction]) -> None:
    part, rest = minimizing_split(contour,
                                  area_requirement=Polygon(contour).area,
                                  key=key)
    assert part == contour
    assert rest is EMPTY


@given(contour=convex_contours,
       area_fraction=negative_fractions,
       key=metrics)
def test_negative_requirement(contour: Contour,
                              area_fraction: Fraction,
                              key: Callable[[Contour, Contour], Fraction]
                              ) -> None:
    area_requirement = area_fraction * Polygon(contour).area
    with pytest.raises(ValueError, match="must not be negative"):
        minimizing_split(contour,
                         area_requirement=area_requirement,
                         key=key)


@given(contour=convex_contours,
       area_excess=positive_nonzero_fractions,
       key=metrics)
def test_excessive_requirement(contour: Contour,
                               area_excess: Fraction,
                               key: Callable[[Contour, Contour], Fraction]
                               ) -> None:
    area_requirement = Polygon(contour).area + area_excess
    with pytest.raises(ValueError, match="exceeds area"):
        minimizing_split(contour,
                         area_requirement=area_requirement,
                         key=key)
