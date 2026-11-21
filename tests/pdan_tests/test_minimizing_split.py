from collections.abc import Callable
from fractions import Fraction

import pytest
from gon.base import (
    EMPTY,
    Contour,
    Orientation,
    Polygon,
)
from hypothesis import given

from pdan.pdan import (
    SupportsLessThan,
    minimizing_split,
    validate_convex_contour,
)
from tests.strategies.base import (
    metrics,
    negative_fractions,
    non_fraction_metrics,
    positive_nonzero_fractions,
)
from tests.strategies.geometry import (
    concave_contours,
    convex_contours,
    convex_contours_with_area_requirements,
)

Key = Callable[[Contour, Contour], SupportsLessThan]


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       key=metrics)
def test_area(contour_with_area_requirement: tuple[Contour, Fraction | float],
              key: Key) -> None:
    contour, area_requirement = contour_with_area_requirement
    part, rest = minimizing_split(contour,
                                  area_requirement=area_requirement,
                                  key=key)
    assert Polygon(part).area == area_requirement
    assert Polygon(part).area + Polygon(rest).area == Polygon(contour).area


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       key=metrics)
def test_union(contour_with_area_requirement: tuple[Contour, Fraction | float],
               key: Key) -> None:
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
                          key: Key) -> None:
    part, rest = minimizing_split(contour,
                                  area_requirement=0,
                                  key=key)
    assert part is EMPTY
    assert rest == contour


@given(contour=convex_contours,
       key=metrics)
def test_full_requirement(contour: Contour,
                          key: Key) -> None:
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
                              key: Key
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
                               key: Key
                               ) -> None:
    area_requirement = Polygon(contour).area + area_excess
    with pytest.raises(ValueError, match="exceeds area"):
        minimizing_split(contour,
                         area_requirement=area_requirement,
                         key=key)


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       key=non_fraction_metrics)
def test_non_fraction_key(
        contour_with_area_requirement: tuple[Contour, Fraction | float],
        key: Key
) -> None:
    contour, area_requirement = contour_with_area_requirement
    part, rest = minimizing_split(contour,
                                  area_requirement=area_requirement,
                                  key=key)
    assert Polygon(part).area == area_requirement
    assert Polygon(part).area + Polygon(rest).area == Polygon(contour).area


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       key=metrics)
def test_orientation_independence(
        contour_with_area_requirement: tuple[Contour, Fraction | float],
        key: Key
) -> None:
    contour, area_requirement = contour_with_area_requirement
    clockwise_result = minimizing_split(contour.to_clockwise(),
                                        area_requirement=area_requirement,
                                        key=key)
    counterclockwise_result = minimizing_split(
        contour.to_counterclockwise(),
        area_requirement=area_requirement,
        key=key)
    assert clockwise_result == counterclockwise_result


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       key=metrics)
def test_counterclockwise_results(
        contour_with_area_requirement: tuple[Contour, Fraction | float],
        key: Key
) -> None:
    contour, area_requirement = contour_with_area_requirement
    part, rest = minimizing_split(contour,
                                  area_requirement=area_requirement,
                                  key=key)
    assert part.orientation is Orientation.COUNTERCLOCKWISE
    assert rest.orientation is Orientation.COUNTERCLOCKWISE


@given(contour=concave_contours,
       key=metrics)
def test_concave(contour: Contour,
                 key: Key) -> None:
    with pytest.raises(ValueError, match="convex"):
        minimizing_split(contour,
                         area_requirement=Polygon(contour).area / 2,
                         key=key)


@given(contour_with_area_requirement=convex_contours_with_area_requirements,
       key=metrics)
def test_parts_are_valid(
        contour_with_area_requirement: tuple[Contour, Fraction | float],
        key: Key
) -> None:
    contour, area_requirement = contour_with_area_requirement
    part, rest = minimizing_split(contour,
                                  area_requirement=area_requirement,
                                  key=key)
    # so that the parts can be split further
    validate_convex_contour(part)
    validate_convex_contour(rest)
