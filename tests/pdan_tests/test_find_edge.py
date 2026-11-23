from fractions import Fraction

import pytest
from gon.base import (
    Contour,
    Point,
    Segment,
)
from hypothesis import (
    example,
    given,
)

from pdan.pdan import find_edge
from tests.strategies.geometry import (
    ccw_convex_contours,
    contours_with_edge_points,
)


@given(contour_with_edge_point=contours_with_edge_points)
def test_edge_point(contour_with_edge_point: tuple[Contour, Segment, Point]
                   ) -> None:
    contour, edge, point = contour_with_edge_point
    result = find_edge(contour, point)
    # segments compare equal regardless of direction
    assert (result.start, result.end) == (edge.start, edge.end)


@given(contour=ccw_convex_contours)
@example(contour=Contour([Point(0, 0), Point(4, 0), Point(0, 4)]))
def test_interior_point(contour: Contour) -> None:
    vertices = contour.vertices
    # the average of the vertices lies strictly inside a convex polygon
    center = Point(sum((vertex.x for vertex in vertices), Fraction(0))
                   / len(vertices),
                   sum((vertex.y for vertex in vertices), Fraction(0))
                   / len(vertices))
    with pytest.raises(ValueError, match="doesn't lie"):
        find_edge(contour, center)
