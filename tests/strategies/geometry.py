from fractions import Fraction
from functools import partial
from typing import (Callable,
                    List,
                    Tuple,
                    TypeVar)

from gon.base import (Contour,
                      Point,
                      Segment)
from gon.base import Polygon
from hypothesis import strategies as st
from hypothesis_geometry import planar
from hypothesis_geometry.hints import Strategy

from pdan.pdan import slope_intercept
from tests.config import (MAX_CONTOUR_SIZE,
                          MAX_HOLES_SIZE)
from tests.pdan_tests.utils import find_vertical_countersegment_end
from tests.strategies.base import fractions

T = TypeVar('T')

TRIANGULAR_CONTOUR_SIZE = 3
QUADRILATERAL_CONTOUR_SIZE = 4

convex_contours = planar.convex_contours(fractions, max_size=MAX_CONTOUR_SIZE)
convex_polygons = st.builds(Polygon, convex_contours)
triangle_contours = planar.convex_contours(
    fractions, max_size=TRIANGULAR_CONTOUR_SIZE)
quadrilateral_contours = planar.convex_contours(
    fractions,
    min_size=QUADRILATERAL_CONTOUR_SIZE,
    max_size=QUADRILATERAL_CONTOUR_SIZE)
polygons = planar.polygons(fractions,
                           max_size=MAX_CONTOUR_SIZE,
                           max_holes_size=MAX_HOLES_SIZE,
                           max_hole_size=MAX_CONTOUR_SIZE)


@st.composite
def to_countersegments_pairs(draw: Callable[[Strategy[T]], T]
                             ) -> Tuple[Segment, Segment]:
    quadrilateral_contour = draw(quadrilateral_contours)
    domain = Segment(quadrilateral_contour.vertices[0],
                     quadrilateral_contour.vertices[1])
    countersegment = Segment(quadrilateral_contour.vertices[2],
                             quadrilateral_contour.vertices[3])
    area = Polygon(Contour([domain.start, domain.end, countersegment.start])
                   ).area
    if countersegment.start.x != countersegment.end.x:
        slope, intercept = slope_intercept(countersegment.start,
                                           quadrilateral_contour.vertices[3])
        countersegment_end_x = (
            (2 * area + domain.end.x * (intercept - countersegment.start.y)
             + countersegment.start.x * (domain.end.y - intercept))
            / (slope * (countersegment.start.x - domain.end.x)
               + domain.end.y - countersegment.start.y))
        countersegment_end_y = (slope * countersegment_end_x
                                + intercept)
    else:
        countersegment_end_x = countersegment.start.x
        countersegment_end_y = (
                2 * area / (countersegment.start.x - domain.end.x)
                + countersegment.start.y)
    countersegment = Segment(countersegment.start,
                             Point(countersegment_end_x,
                                   countersegment_end_y))
    return domain, countersegment


countersegments_pairs = to_countersegments_pairs()

unique_coordinate_pairs = st.lists(fractions,
                                   min_size=2,
                                   max_size=2,
                                   unique=True)
unique_increasing_coordinate_pairs = unique_coordinate_pairs.map(sorted)
unique_decreasing_coordinate_pairs = unique_coordinate_pairs.map(
    partial(sorted, reverse=True))


def _to_vertical_countersegments_and_area(
        coordinates: Tuple[List[Fraction], List[Fraction], Fraction]
        ) -> Tuple[Segment, Segment, Fraction]:
    xs, ys_left, y_right_start = coordinates
    domain_start = Point(xs[0], ys_left[0])
    domain_end = Point(xs[0], ys_left[1])
    domain = Segment(domain_start, domain_end)
    countersegment_start = Point(xs[1], y_right_start)
    area = Polygon(Contour([domain_start,
                            domain_end,
                            countersegment_start])).area
    y_right_end = find_vertical_countersegment_end(
        domain_end=domain_end,
        countersegment_start=countersegment_start,
        area=area).y
    countersegment = Segment(Point(xs[1], y_right_start),
                             Point(xs[1], y_right_end))
    return domain, countersegment, area


vertical_ccw_segments_and_areas = st.tuples(
    unique_increasing_coordinate_pairs,
    unique_decreasing_coordinate_pairs,
    fractions).map(_to_vertical_countersegments_and_area)

fraction_points = planar.points(fractions)
points_pairs = st.lists(fraction_points,
                        min_size=2,
                        max_size=2,
                        unique=True)
