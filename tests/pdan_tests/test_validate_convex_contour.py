import pytest
from gon.base import (
    Contour,
    Point,
)
from hypothesis import given

from pdan.pdan import validate_convex_contour
from tests.strategies.geometry import (
    any_orientation_convex_contours,
    collinear_contours,
    concave_contours,
    contours_with_collinear_vertex,
    contours_with_repeated_vertex,
    points_pairs,
    star_contours,
)


@given(any_orientation_convex_contours)
def test_convex(contour: Contour) -> None:
    validate_convex_contour(contour)


@given(contours_with_collinear_vertex)
def test_collinear_vertex(contours: tuple[Contour, Contour]) -> None:
    _, contour = contours
    with pytest.raises(ValueError, match="same line"):
        validate_convex_contour(contour)


@given(concave_contours)
def test_concave(contour: Contour) -> None:
    with pytest.raises(ValueError, match="convex"):
        validate_convex_contour(contour)


@given(star_contours)
def test_star(contour: Contour) -> None:
    with pytest.raises(ValueError, match="self-intersecting"):
        validate_convex_contour(contour)


@given(contours_with_repeated_vertex)
def test_repeated_vertex(contour: Contour) -> None:
    with pytest.raises(ValueError, match="same line"):
        validate_convex_contour(contour)


@given(collinear_contours)
def test_all_collinear(contour: Contour) -> None:
    with pytest.raises(ValueError, match="same line"):
        validate_convex_contour(contour)


@given(points_pairs)
def test_too_few_vertices(points: list[Point]) -> None:
    with pytest.raises(ValueError, match="at least 3"):
        validate_convex_contour(Contour(points))
