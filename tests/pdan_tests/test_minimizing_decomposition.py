from collections.abc import Callable
from fractions import Fraction

import pytest
from gon.base import (
    EMPTY,
    Contour,
    Orientation,
    Point,
    Polygon,
)
from hypothesis import (
    given,
)
from hypothesis import (
    strategies as st,
)

from pdan.pdan import (
    SupportsLessThan,
    minimizing_decomposition,
    minimizing_split,
    validate_convex_contour,
)
from tests.strategies.base import (
    non_fraction_metrics,
    positive_nonzero_fractions,
)
from tests.strategies.geometry import (
    concave_contours,
    convex_contours,
    convex_contours_with_area_requirements_lists,
)

Key = Callable[[Contour, Contour], SupportsLessThan]
ContourWithRequirements = tuple[Contour, list[Fraction]]

# exact perimeters (`Contour.length`) are too slow to compare
# for the parts of decompositions
keys = non_fraction_metrics
precisions = st.none() | st.integers(1, 128)


def squared_diameter(contour: Contour) -> Fraction:
    return max(Fraction((start.x - end.x) ** 2 + (start.y - end.y) ** 2)
               for start in contour.vertices
               for end in contour.vertices)


@given(contour_with_requirements=convex_contours_with_area_requirements_lists,
       key=keys,
       precision_bits=precisions)
def test_areas(contour_with_requirements: ContourWithRequirements,
               key: Key,
               precision_bits: int | None) -> None:
    contour, requirements = contour_with_requirements
    parts = minimizing_decomposition(contour, requirements, key=key,
                                     precision_bits=precision_bits)
    assert len(parts) == len(requirements)
    tolerance = (0
                 if precision_bits is None
                 else (Fraction(2, 1 << precision_bits)
                       * squared_diameter(contour)))
    for part, requirement in zip(parts, requirements, strict=True):
        if requirement == 0:
            assert part is EMPTY
        else:
            assert abs(Polygon(part).area - requirement) <= tolerance
    assert (sum((Polygon(part).area for part in parts if part is not EMPTY),
                start=Fraction(0))
            == Polygon(contour).area)


@given(contour_with_requirements=convex_contours_with_area_requirements_lists,
       key=keys,
       precision_bits=precisions)
def test_union(contour_with_requirements: ContourWithRequirements,
               key: Key,
               precision_bits: int | None) -> None:
    contour, requirements = contour_with_requirements
    parts = minimizing_decomposition(contour, requirements, key=key,
                                     precision_bits=precision_bits)
    polygons = [Polygon(part) for part in parts if part is not EMPTY]
    union = polygons[0]
    for polygon in polygons[1:]:
        union |= polygon
    assert isinstance(union, Polygon)
    assert union.border == contour.to_counterclockwise()


@given(contour_with_requirements=convex_contours_with_area_requirements_lists,
       key=keys,
       precision_bits=precisions)
def test_parts_are_valid(contour_with_requirements: ContourWithRequirements,
                         key: Key,
                         precision_bits: int | None) -> None:
    contour, requirements = contour_with_requirements
    parts = minimizing_decomposition(contour, requirements, key=key,
                                     precision_bits=precision_bits)
    for part in parts:
        if part is not EMPTY:
            validate_convex_contour(part)
            assert part.orientation is Orientation.COUNTERCLOCKWISE


@given(contour_with_requirements=convex_contours_with_area_requirements_lists,
       key=keys)
def test_largest_first(contour_with_requirements: ContourWithRequirements,
                       key: Key) -> None:
    contour, requirements = contour_with_requirements
    parts = minimizing_decomposition(contour, requirements, key=key,
                                     precision_bits=None)
    largest_index = max(range(len(requirements)),
                        key=requirements.__getitem__)
    if sum(requirement > 0 for requirement in requirements) > 1:
        expected, _ = minimizing_split(contour,
                                       requirements[largest_index],
                                       key=key)
        assert parts[largest_index] == expected


@given(contour=convex_contours,
       key=keys,
       precision_bits=precisions)
def test_single_requirement(contour: Contour,
                            key: Key,
                            precision_bits: int | None) -> None:
    parts = minimizing_decomposition(contour, [Polygon(contour).area],
                                     key=key,
                                     precision_bits=precision_bits)
    assert parts == [contour.to_counterclockwise()]


@given(contour=convex_contours,
       excess=positive_nonzero_fractions,
       key=keys)
def test_wrong_sum(contour: Contour,
                   excess: Fraction,
                   key: Key) -> None:
    area = Polygon(contour).area
    with pytest.raises(ValueError, match="sum to"):
        minimizing_decomposition(contour, [area / 2, area / 2 + excess],
                                 key=key)
    with pytest.raises(ValueError, match="sum to"):
        minimizing_decomposition(contour, [], key=key)


@given(contour=convex_contours,
       excess=positive_nonzero_fractions,
       key=keys)
def test_negative_requirement(contour: Contour,
                              excess: Fraction,
                              key: Key) -> None:
    area = Polygon(contour).area
    with pytest.raises(ValueError, match="must not be negative"):
        minimizing_decomposition(contour, [area + excess, -excess],
                                 key=key)


@given(contour=convex_contours,
       precision_bits=st.integers(max_value=0),
       key=keys)
def test_nonpositive_precision(contour: Contour,
                               precision_bits: int,
                               key: Key) -> None:
    with pytest.raises(ValueError, match="Precision must be positive"):
        minimizing_decomposition(contour, [Polygon(contour).area],
                                 key=key,
                                 precision_bits=precision_bits)


@given(contour=concave_contours,
       key=keys)
def test_concave(contour: Contour,
                 key: Key) -> None:
    area = Polygon(contour).area
    with pytest.raises(ValueError, match="convex"):
        minimizing_decomposition(contour, [area / 2, area / 2], key=key)


def test_many_parts() -> None:
    contour = Contour([Point(0, 0), Point(7, 0), Point(9, 4), Point(5, 8),
                       Point(-1, 5)])
    count = 30
    requirements = [Polygon(contour).area / count] * count
    parts = minimizing_decomposition(
        contour, requirements,
        key=lambda part, _rest: len(part.vertices))
    assert len(parts) == count
    denominators_bits = max(max(vertex.x.denominator.bit_length(),
                                vertex.y.denominator.bit_length())
                            for part in parts
                            for vertex in part.vertices)
    # grows linearly with the number of cuts rather than exponentially
    assert denominators_bits <= 100 * count
