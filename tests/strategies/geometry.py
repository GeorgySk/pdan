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

from pdan.pdan import (
    minimizing_split,
    slope_intercept,
)
from tests.config import MAX_CONTOUR_SIZE
from tests.pdan_tests.utils import find_vertical_countersegment_end
from tests.strategies.base import (
    coordinates,
    fraction_requirements,
    fractions,
    metrics,
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


@st.composite
def to_convex_contours_with_area_requirements_lists(
        draw: st.DrawFn) -> tuple[Contour, list[Fraction]]:
    contour = draw(any_coordinates_convex_contours)
    if draw(st.booleans()):
        contour = contour.to_clockwise()
    area = Polygon(contour).area
    shares = draw(fraction_requirements)
    if draw(st.booleans()):
        # equal requirements must keep their order
        shares = [shares[0], *shares]
        shares = [share / sum(shares) for share in shares]
    requirements = [share * area for share in shares]
    zeros_count = draw(st.integers(0, 2))
    for _ in range(zeros_count):
        index = draw(st.integers(0, len(requirements)))
        requirements.insert(index, Fraction(0))
    return contour, requirements


convex_contours_with_area_requirements_lists = (
    to_convex_contours_with_area_requirements_lists())


MAX_SPLIT_PRECISION_BITS = 128
split_precisions = st.integers(1, MAX_SPLIT_PRECISION_BITS)
ccw_convex_contours = convex_contours.map(Contour.to_counterclockwise)


def _interpolate(start: Point, end: Point, position: Fraction) -> Point:
    return Point(start.x + position * (end.x - start.x),
                 start.y + position * (end.y - start.y))


@st.composite
def to_contours_with_indices(draw: st.DrawFn) -> tuple[Contour, int]:
    contour = draw(ccw_convex_contours)
    return contour, draw(st.integers(0, len(contour.vertices) - 1))


contours_with_indices = to_contours_with_indices()


@st.composite
def to_contours_with_edge_points(
        draw: st.DrawFn) -> tuple[Contour, Segment, Point]:
    contour, index = draw(contours_with_indices)
    vertices = contour.vertices
    edge = Segment(vertices[index], vertices[(index + 1) % len(vertices)])
    position = draw(open_interval_unit_fractions)
    return contour, edge, _interpolate(edge.start, edge.end, position)


contours_with_edge_points = to_contours_with_edge_points()


@st.composite
def to_splits(draw: st.DrawFn) -> tuple[Contour, Contour, Contour]:
    contour = draw(ccw_convex_contours)
    area_requirement = (draw(open_interval_unit_fractions)
                        * Polygon(contour).area)
    part, rest = minimizing_split(contour, area_requirement,
                                  key=draw(metrics))
    return contour, part, rest


splits = to_splits()


@st.composite
def to_collapsing_splits(
        draw: st.DrawFn) -> tuple[Contour, Contour, Contour, int]:
    # cuts off a corner so close to its vertex that rounding
    # moves both splitter endpoints onto the vertex
    contour, index = draw(contours_with_indices)
    vertices = contour.vertices
    size = len(vertices)
    previous = vertices[index - 1]
    vertex = vertices[index]
    next_ = vertices[(index + 1) % size]
    precision_bits = draw(split_precisions)
    step = Fraction(1, 1 << precision_bits)
    before = _interpolate(previous, vertex,
                          1 - draw(open_interval_unit_fractions) * step)
    after = _interpolate(vertex, next_,
                         draw(open_interval_unit_fractions) * step)
    part = Contour([before, vertex, after])
    rest = Contour([after,
                    *[vertices[(index + offset) % size]
                      for offset in range(1, size)],
                    before])
    return contour, part, rest, precision_bits


collapsing_splits = to_collapsing_splits()
