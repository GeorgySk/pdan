from gon.base import (
    Contour,
    Point,
)
from hypothesis import (
    example,
    given,
)

from pdan.pdan import replace_vertices
from tests.strategies.geometry import (
    ccw_convex_contours,
    contours_with_indices,
)


@given(contour=ccw_convex_contours)
def test_no_replacements(contour: Contour) -> None:
    assert replace_vertices(contour, {}).vertices == contour.vertices


@given(contour_with_index=contours_with_indices)
@example(contour_with_index=(Contour([Point(0, 0), Point(2, 0),
                                      Point(2, 2), Point(0, 2)]),
                             0))
def test_merging_with_previous(contour_with_index: tuple[Contour, int]
                               ) -> None:
    contour, index = contour_with_index
    vertices = contour.vertices
    result = replace_vertices(contour, {vertices[index]: vertices[index - 1]})
    expected = [*vertices[:index], *vertices[index + 1:]]
    assert len(result.vertices) == len(expected)
    assert set(result.vertices) == set(expected)
    # no repeated vertices, including the last and the first ones
    assert all(vertex != result.vertices[position - 1]
               for position, vertex in enumerate(result.vertices))
