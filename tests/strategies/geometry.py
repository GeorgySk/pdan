from fractions import Fraction
from functools import partial

from gon.base import (
    Contour,
    Point,
    Polygon,
    Segment,
)
from hypothesis import strategies as st
from hypothesis_geometry import planar

from pdan.pdan import slope_intercept
from tests.config import MAX_CONTOUR_SIZE
from tests.pdan_tests.utils import find_vertical_countersegment_end
from tests.strategies.base import (
    coordinates,
    fractions,
    open_interval_unit_fractions,
)

TRIANGULAR_CONTOUR_SIZE = 3
QUADRILATERAL_CONTOUR_SIZE = 4

convex_contours = planar.convex_contours(fractions, max_size=MAX_CONTOUR_SIZE)
any_coordinates_convex_contours = planar.convex_contours(
    coordinates, max_size=MAX_CONTOUR_SIZE)
triangle_contours = planar.convex_contours(
    fractions, max_size=TRIANGULAR_CONTOUR_SIZE)
quadrilateral_contours = planar.convex_contours(
    fractions,
    min_size=QUADRILATERAL_CONTOUR_SIZE,
    max_size=QUADRILATERAL_CONTOUR_SIZE)


@st.composite
def to_convex_contours_with_area_requirements(
        draw: st.DrawFn) -> tuple[Contour, Fraction | float]:
    contour = draw(any_coordinates_convex_contours)
    if draw(st.booleans()):
        contour = contour.to_clockwise()
    unit_fraction = draw(open_interval_unit_fractions)
    area_requirement = unit_fraction * Polygon(contour).area
    converters: list[type[Fraction | float]] = [Fraction, float]
    if area_requirement.denominator == 1:
        converters.append(int)
    convert = draw(st.sampled_from(converters))
    return contour, convert(area_requirement)


convex_contours_with_area_requirements = (
    to_convex_contours_with_area_requirements())


@st.composite
def to_countersegments_pairs(draw: st.DrawFn) -> tuple[Segment, Segment]:
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
        coordinates: tuple[list[Fraction], list[Fraction], Fraction]
        ) -> tuple[Segment, Segment, Fraction]:
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


def _reverse_maybe(contour: Contour,
                   *,
                   reverse: bool) -> Contour:
    return contour.to_clockwise() if reverse else contour


any_orientation_convex_contours = st.builds(_reverse_maybe,
                                            convex_contours,
                                            reverse=st.booleans())
concave_contours = planar.concave_contours(fractions,
                                           max_size=MAX_CONTOUR_SIZE)


def _to_star(contour: Contour) -> Contour:
    # visiting every second vertex of a convex polygon with an odd number
    # of vertices turns in one direction but winds around twice
    vertices = contour.vertices
    return Contour([*vertices[::2], *vertices[1::2]])


STAR_MIN_SIZE = 5
star_contours = (planar.convex_contours(fractions,
                                        min_size=STAR_MIN_SIZE,
                                        max_size=max(STAR_MIN_SIZE,
                                                     MAX_CONTOUR_SIZE))
                 .filter(lambda contour: len(contour.vertices) % 2 == 1)
                 .map(_to_star))


@st.composite
def to_contours_with_repeated_vertex(draw: st.DrawFn) -> Contour:
    vertices = draw(any_orientation_convex_contours).vertices
    index = draw(st.integers(0, len(vertices) - 1))
    return Contour([*vertices[:index + 1], *vertices[index:]])


contours_with_repeated_vertex = to_contours_with_repeated_vertex()


@st.composite
def to_collinear_contours(draw: st.DrawFn) -> Contour:
    start, end = draw(points_pairs)
    parameters = draw(st.lists(fractions, min_size=3,
                               max_size=MAX_CONTOUR_SIZE, unique=True))
    return Contour([Point(start.x + parameter * (end.x - start.x),
                          start.y + parameter * (end.y - start.y))
                    for parameter in parameters])


collinear_contours = to_collinear_contours()


@st.composite
def to_contours_with_collinear_vertex(
        draw: st.DrawFn) -> tuple[Contour, Contour]:
    contour = draw(any_orientation_convex_contours)
    vertices = contour.vertices
    index = draw(st.integers(0, len(vertices) - 1))
    start, end = vertices[index], vertices[(index + 1) % len(vertices)]
    midpoint = Point((start.x + end.x) / 2, (start.y + end.y) / 2)
    return contour, Contour([*vertices[:index + 1], midpoint,
                             *vertices[index + 1:]])


contours_with_collinear_vertex = to_contours_with_collinear_vertex()
