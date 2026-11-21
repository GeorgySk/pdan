"""
Splits convex polygons into two parts with a given area.

Implements the algorithm of Skorobogatov et al., 2021, which finds
among all splits of a convex polygon that cut off a part with
the given area the one that minimizes a user-supplied `key` function.
"""

from collections import deque
from collections.abc import (
    Callable,
    Iterator,
)
from dataclasses import dataclass
from fractions import Fraction
from math import isqrt
from typing import (
    Protocol,
    Self,
    TypeVar,
)

from gon.base import (
    EMPTY,
    Contour,
    Orientation,
    Point,
    Polygon,
    Segment,
)
from gon.hints import Maybe

ROOT_PRECISION_BITS = 96
"""Relative precision of inexact roots, close to 28 decimal digits."""


class SupportsLessThan(Protocol):
    """
    Describes values that can be ordered with the `<` operator.

    Covers `int`, `float`, `Fraction`, the values of `Contour.length`
    and any other type whose instances compare with each other.
    """

    def __lt__(self, other: Self, /) -> bool:
        """
        Checks if the value is less than the other one.

        :param other: value of the same type to compare with
        :return: whether the value is less than `other`
        """
        ...


KeyValue = TypeVar("KeyValue", bound=SupportsLessThan)
"""Type of the values that `key` returns in `minimizing_split`."""


@dataclass
class Partition:
    """
    Describes a candidate place to split the polygon.

    Holds a "domain" segment and its "countersegment" on the polygon
    boundary, the vertices of the polygon lying on each side between
    them, and the area that a splitter segment connecting the two
    still has to cut off.

    :ivar domain: segment of the boundary where a splitter starts
    :ivar countersegment: segment of the boundary where a splitter ends
    :ivar right_vertices: vertices going counterclockwise from `domain`
        to `countersegment`; empty if there are none between them
    :ivar left_vertices: vertices going counterclockwise from
        `countersegment` to `domain`; empty if there are none between them
    :ivar area_difference: area to cut off from the quadrilateral
        between `domain` and `countersegment`
    """

    domain: Segment
    countersegment: Segment
    right_vertices: list[Point]
    left_vertices: list[Point]
    area_difference: Fraction


def minimizing_split(contour: Contour,
                     area_requirement: Fraction | float,
                     *,
                     key: Callable[[Contour, Contour], KeyValue]
                     ) -> tuple[Maybe[Contour], Maybe[Contour]]:
    """
    Splits convex polygon into two parts minimizing `key` function.

    Finds the part of the polygon defined by the input contour
    with the given area requirement that yields the minimum possible
    value when applied to `key` function, and returns it along with
    the remaining part as contours.

    Floats are converted to fractions exactly, so `0.1` becomes
    `3602879701896397/36028797018963968`, the value the float actually
    stores, and the results compare equal to the float inputs.
    To work with exact decimal values, pass fractions instead,
    for example `Fraction("0.1")`.

    The area of the returned part always equals the area requirement
    exactly. The splitter is the shortest one between the edges
    it connects, but its endpoints may be irrational, for example
    when cutting off area 3 from a 4 by 4 square. In such cases,
    one endpoint is rounded to `ROOT_PRECISION_BITS` significant bits,
    and the other one is placed so that the area stays exact.
    The splitter is then optimal up to a relative error of about
    `2 ** -(2 * ROOT_PRECISION_BITS)` in its length, and the
    coordinates have denominators of about that many bits.

    :param contour: defines a convex polygon; integer and float
        coordinates are converted to fractions
    :param area_requirement: area of a part to return; converted
        to a fraction if given as an integer or a float
    :param key: function to be applied to a pair of contours;
        its values only need to support comparison with `<`
    :return: two contours if the area requirement is between zero
        and area of the polygon; empty geometry and a copy of the input
        contour with fraction coordinates if it is zero; that copy and
        empty geometry if it is equal to area of the polygon.
    :raises ValueError: if the area requirement is negative
        or exceeds area of the polygon.
    """
    contour = to_fraction_contour(contour)
    area_requirement = Fraction(area_requirement)
    area = Polygon(contour).area
    if area_requirement < 0:
        raise ValueError("Area requirement must not be negative, "
                         f"but got {area_requirement}.")
    if area_requirement > area:
        raise ValueError(f"Area requirement {area_requirement} exceeds "
                         f"area of the polygon {area}.")
    if area_requirement == 0:
        return EMPTY, contour
    if area_requirement == area:
        return contour, EMPTY
    partitions = to_partitions(contour=contour,
                               area_requirement=area_requirement)
    return min(map(to_split_contours, partitions),
               key=lambda contours: key(*contours))


def to_split_contours(partition: Partition) -> tuple[Contour, Contour]:
    """
    Splits the polygon at the given partition.

    Finds the splitter between the domain and the countersegment
    of the partition and builds the contours on both sides of it.

    :param partition: candidate place to split the polygon
    :return: contours of the parts to the right and to the left
        of the splitter.
    """
    splitter = to_splitter(domain=partition.domain,
                           countersegment=partition.countersegment,
                           area_requirement=partition.area_difference)
    return to_right_left_contours(domain=partition.domain,
                                  countersegment=partition.countersegment,
                                  splitter=splitter,
                                  right_vertices=partition.right_vertices,
                                  left_vertices=partition.left_vertices)


def to_fraction_contour(contour: Contour) -> Contour:
    """
    Converts coordinates of contour vertices to fractions.

    The algorithm relies on exact arithmetic, while integer or float
    coordinates would make divisions return floats.

    :param contour: contour with integer, float or fraction coordinates
    :return: same contour with fraction coordinates
    """
    return Contour([Point(Fraction(vertex.x), Fraction(vertex.y))
                    for vertex in contour.vertices])


def to_partitions(contour: Contour,  # noqa: PLR0915
                  area_requirement: Fraction) -> Iterator[Partition]:
    """
    Returns an iterator over `Partition` objects of the given contour.

    The partitions contain information about domain segments,
    their countersegments, "right" and "left" parts' vertices,
    where "right" vertices are all the original vertices
    located between the domain and countersegment when iterating
    in counterclockwise order, and left vertices are
    all the original vertices located between the countersegment and
    domain segment when iterating in counterclockwise order,
    and, finally, the area differences that should be found in the
    quadrilateral based on the domains and the countersegments.

    :param contour: defines a convex polygon, with fraction coordinates
    :param area_requirement: area of the part to the right
        of a splitter, strictly between zero and area of the polygon
    :return: partitions in the order of the sweep around the contour.
    """
    segments = contour.segments
    # in gon, the last segment goes first, the first one goes second, and so on
    edges = iter([*segments[1:], segments[0]])
    counteredges = iter([*segments[2:], *segments])
    edge = next(edges)
    accumulated_area = Fraction(0)
    right_vertices = deque([edge.start])
    left_vertices = deque(contour.vertices[1:])
    # `counteredges` spans more than a full turn, and the triangles fanned
    # from `edge.start` cover the whole polygon in fewer steps,
    # so the loop always breaks for an area requirement below its area
    for counteredge in counteredges:
        right_vertices.append(counteredge.start)
        left_vertices.popleft()
        covered_triangle_area = Polygon(Contour([edge.start,
                                                 counteredge.start,
                                                 counteredge.end])).area
        accumulated_area += covered_triangle_area
        if accumulated_area < area_requirement:
            continue
        elif accumulated_area == area_requirement:
            right_vertices.append(counteredge.end)
            left_vertices.popleft()
            counteredge = next(counteredges)  # noqa: PLW2901
            countervertex = counteredge.start
            is_countervertex_original = True
        else:
            area = covered_triangle_area + area_requirement - accumulated_area
            countervertex = inverse_shoelace(area=area,
                                             endpoint=edge.start,
                                             base_start=counteredge.start,
                                             base_end=counteredge.end)
            right_vertices.append(countervertex)
            is_countervertex_original = False
        break
    is_edge_start_original = True
    while True:
        edge_triangle_area = Polygon(Contour([edge.start,
                                              edge.end,
                                              countervertex])).area
        counteredge_triangle_area = Polygon(Contour([edge.end,
                                                     countervertex,
                                                     counteredge.end])).area
        right_vertices.popleft()
        left_vertices.append(edge.start)
        if edge_triangle_area == counteredge_triangle_area:
            domain = edge
            domain_based_area = edge_triangle_area
            countersegment_end = counteredge.end
            edge = next(edges, None)
            counteredge = next(counteredges)
        elif counteredge_triangle_area > edge_triangle_area:
            domain = edge
            domain_based_area = edge_triangle_area
            countersegment_end = inverse_shoelace(area=edge_triangle_area,
                                                  endpoint=edge.end,
                                                  base_start=countervertex,
                                                  base_end=counteredge.end)
            left_vertices.appendleft(countersegment_end)
            edge = next(edges, None)
            counteredge = Segment(countersegment_end, counteredge.end)
        else:
            area_difference = (edge_triangle_area
                               - counteredge_triangle_area)
            domain_end = inverse_shoelace(area=area_difference,
                                          endpoint=counteredge.end,
                                          base_start=edge.end,
                                          base_end=edge.start)
            right_vertices.appendleft(domain_end)
            domain = Segment(edge.start, domain_end)
            domain_based_area = Polygon(Contour([domain.start,
                                                 domain.end,
                                                 countervertex])).area
            countersegment_end = counteredge.end
            edge = Segment(domain_end, edge.end)
            counteredge = next(counteredges)
        countersegment = Segment(countervertex, countersegment_end)
        right_vertices_list = list(right_vertices)
        resulting_right_vertices = (right_vertices_list
                                    if right_vertices_list[1:-1] else [])
        left_vertices_list = list(left_vertices)
        resulting_left_vertices = (left_vertices_list
                                   if left_vertices_list[1:-1] else [])
        yield Partition(domain=domain,
                        countersegment=countersegment,
                        right_vertices=resulting_right_vertices,
                        left_vertices=resulting_left_vertices,
                        area_difference=domain_based_area)
        if edge is None:
            return
        countervertex = counteredge.start
        if not is_countervertex_original:
            right_vertices.pop()
        if not is_edge_start_original:
            left_vertices.pop()
        right_vertices.append(countervertex)
        left_vertices.popleft()
        is_countervertex_original = (counteredge_triangle_area
                                     <= edge_triangle_area)
        is_edge_start_original = (counteredge_triangle_area
                                  >= edge_triangle_area)


def to_splitter(domain: Segment,
                countersegment: Segment,
                area_requirement: Fraction) -> Segment:
    """
    Finds "splitter" segment cutting off the given area requirement.

    For the given "domain" and its corresponding "countersegment",
    finds another "splitter" segment connecting these two
    so that the area on the right would be
    equal to the given area requirement.

    :param domain: segment of the boundary where the splitter starts
    :param countersegment: segment of the boundary where the splitter
        ends
    :param area_requirement: area of the quadrilateral formed by
        the splitter, the end of `domain` and the start
        of `countersegment`
    :return: splitter with the start on `domain` and the end
        on `countersegment`; the segment connecting the starts
        or the ends of both if the optimal splitter lies beyond them.
    """
    if (domain.start.x == domain.end.x
            and countersegment.end.x == countersegment.start.x):
        return vertical_segments_splitter(area_requirement=area_requirement,
                                          domain=domain,
                                          countersegment=countersegment)
    if domain.start.x == domain.end.x:
        return vertical_domain_splitter(area_requirement=area_requirement,
                                        domain=domain,
                                        countersegment=countersegment)
    if countersegment.start.x == countersegment.end.x:
        return vertical_countersegment_splitter(
            area_requirement=area_requirement,
            domain=domain,
            countersegment=countersegment)
    domain_slope, domain_intercept = slope_intercept(domain.start,
                                                     domain.end)
    countersegment_slope, countersegment_intercept = slope_intercept(
        countersegment.start,
        countersegment.end)
    intercept_diff = domain_intercept - countersegment_intercept
    if countersegment_slope == domain_slope:
        return parallel_inclined_segments_splitter(
            area_requirement=area_requirement,
            intercept_diff=intercept_diff,
            domain=domain,
            domain_intercept=domain_intercept,
            countersegment=countersegment,
            countersegment_intercept=countersegment_intercept,
            slope=domain_slope)
    return general_case_splitter(
        area_requirement=area_requirement,
        intercept_diff=intercept_diff,
        domain=domain,
        domain_intercept=domain_intercept,
        domain_slope=domain_slope,
        countersegment=countersegment,
        countersegment_intercept=countersegment_intercept,
        countersegment_slope=countersegment_slope)


def to_right_left_contours(domain: Segment,  # noqa: PLR0912, C901
                           countersegment: Segment,
                           splitter: Segment,
                           right_vertices: list[Point],
                           left_vertices: list[Point]) -> tuple[Contour,
                                                                Contour]:
    """
    Constructs right and left contours separated by the splitter.

    The contours are built from the splitter and vertices delimiting
    right and left parts based on the splitter's endpoints location.

    :param domain: segment of the boundary where the splitter starts
    :param countersegment: segment of the boundary where the splitter
        ends
    :param splitter: segment connecting `domain` and `countersegment`
    :param right_vertices: vertices going counterclockwise from
        `domain` to `countersegment`; empty if there are none
        between them
    :param left_vertices: vertices going counterclockwise from
        `countersegment` to `domain`; empty if there are none
        between them
    :return: contours of the parts to the right and to the left
        of the splitter, without collinear vertices at its endpoints.
    """
    if not right_vertices:
        if splitter.start == domain.start:
            right_contour = Contour([domain.start, domain.end,
                                     countersegment.start])
        elif splitter.start == domain.end:
            right_contour = Contour([domain.end, countersegment.start,
                                     countersegment.end])
        else:
            right_contour = Contour([splitter.start, domain.end,
                                     countersegment.start, splitter.end])
    else:
        if domain.end in Segment(splitter.start, right_vertices[1]):
            right_vertices = right_vertices[1:]
        if countersegment.start in Segment(right_vertices[-2], splitter.end):
            right_vertices = right_vertices[:-1]
        right_contour = Contour([splitter.start,
                                 *right_vertices,
                                 splitter.end])
    if not left_vertices:
        if splitter.start == domain.start:
            left_contour = Contour([countersegment.start, countersegment.end,
                                    domain.start])
        elif splitter.start == domain.end:
            left_contour = Contour([countersegment.end, domain.start,
                                    domain.end])
        else:
            left_contour = Contour([splitter.end, countersegment.end,
                                    domain.start, splitter.start])
    else:
        if domain.start in Segment(left_vertices[-2], splitter.start):
            left_vertices = left_vertices[:-1]
        if countersegment.end in Segment(splitter.end, left_vertices[1]):
            left_vertices = left_vertices[1:]
        left_contour = Contour([splitter.end, *left_vertices, splitter.start])
    return right_contour, left_contour


def vertical_segments_splitter(area_requirement: Fraction,
                               domain: Segment,
                               countersegment: Segment) -> Segment:
    """
    Finds splitter for vertical domain and countersegment.

    Finds segment connecting two vertical "domain"
    and "countersegment" segments
    so that the area on the right would be
    equal to the area requirement.

    :param area_requirement: area to the right of the splitter
        between `domain` and `countersegment`
    :param domain: vertical segment where the splitter starts
    :param countersegment: vertical segment where the splitter ends
    :return: splitter, or the segment connecting the starts
        or the ends of both segments if it lies beyond them.
    """
    tail_y = ((2 * area_requirement
               + countersegment.start.x * countersegment.start.y
               + countersegment.start.x * domain.end.y
               - domain.start.x * domain.end.y
               - domain.start.x * countersegment.start.y)
              / (2 * (countersegment.start.x - domain.start.x)))
    if is_before_domain(tail_y, domain.start.y, domain.end.y):
        return Segment(domain.start, countersegment.start)
    if is_after_domain(tail_y, domain.start.y, domain.end.y):
        return Segment(domain.end, countersegment.end)
    tail_point = Point(domain.end.x, tail_y)
    head_point = Point(countersegment.start.x, tail_y)
    return Segment(tail_point, head_point)


def vertical_domain_splitter(area_requirement: Fraction,
                             domain: Segment,
                             countersegment: Segment) -> Segment:
    """
    Finds splitter for vertical domain and inclined countersegment.

    Finds segment connecting a vertical "domain"
    and an inclined "countersegment" segments
    so that the area on the right would be
    equal to the area requirement.

    :param area_requirement: area to the right of the splitter
        between `domain` and `countersegment`
    :param domain: vertical segment where the splitter starts
    :param countersegment: inclined segment where the splitter ends
    :return: splitter, or the segment connecting the starts
        or the ends of both segments if it lies beyond them.
    """
    slope, intercept = slope_intercept(countersegment.start,
                                       countersegment.end)
    lines_intersection_y = slope * domain.end.x + intercept
    const = (2 * area_requirement
             - lines_intersection_y * countersegment.start.x
             + domain.end.y * (countersegment.start.x - domain.end.x))
    fourth_power_tail_intersection_diff_y = (
            (lines_intersection_y * domain.end.x + const) ** 2
            * (1 + slope ** 2))
    sign = 1 if lines_intersection_y < domain.end.y else -1
    tail_intersection_diff_y = fourth_root(
        fourth_power_tail_intersection_diff_y)
    tail_y = sign * tail_intersection_diff_y + lines_intersection_y
    if is_before_domain(tail_y, domain.start.y, domain.end.y):
        return Segment(domain.start, countersegment.start)
    if is_after_domain(tail_y, domain.start.y, domain.end.y):
        return Segment(domain.end, countersegment.end)
    head_x = ((const + domain.end.x * tail_y)
              / (tail_y - lines_intersection_y))
    head_y = slope * head_x + intercept
    tail_point = Point(domain.end.x, tail_y)
    head_point = Point(head_x, head_y)
    return Segment(tail_point, head_point)


def vertical_countersegment_splitter(area_requirement: Fraction,
                                     domain: Segment,
                                     countersegment: Segment) -> Segment:
    """
    Finds splitter for inclined domain and vertical countersegment.

    Finds segment connecting an inclined "domain"
    and a vertical "countersegment" segments
    so that the area on the right would be
    equal to the area requirement.

    :param area_requirement: area to the right of the splitter
        between `domain` and `countersegment`
    :param domain: inclined segment where the splitter starts
    :param countersegment: vertical segment where the splitter ends
    :return: splitter, or the segment connecting the starts
        or the ends of both segments if it lies beyond them.
    """
    slope, intercept = slope_intercept(domain.start, domain.end)
    const = (2 * area_requirement
             + slope * domain.end.x * countersegment.start.x
             + intercept * domain.end.x - countersegment.start.y * domain.end.x
             + countersegment.start.x * countersegment.start.y)
    lines_intersection_y = slope * countersegment.start.x + intercept
    fourth_power_tail_intersection_diff_x = (
            (const - lines_intersection_y * countersegment.start.x) ** 2
            / (1 + slope ** 2))
    sign = 1 if domain.start.x > countersegment.end.x else -1
    tail_intersection_diff_x = fourth_root(
        fourth_power_tail_intersection_diff_x)
    tail_x = countersegment.start.x + sign * tail_intersection_diff_x
    if is_before_domain(tail_x, domain.start.x, domain.end.x):
        return Segment(domain.start, countersegment.start)
    if is_after_domain(tail_x, domain.start.x, domain.end.x):
        return Segment(domain.end, countersegment.end)
    tail_y = tail_x * slope + intercept
    head_y = ((const - tail_x * lines_intersection_y)
              / (countersegment.start.x - tail_x))
    tail_point = Point(tail_x, tail_y)
    head_point = Point(countersegment.start.x, head_y)
    return Segment(tail_point, head_point)


def parallel_inclined_segments_splitter(*,  # noqa: PLR0913
                                        area_requirement: Fraction,
                                        intercept_diff: Fraction,
                                        domain: Segment,
                                        domain_intercept: Fraction,
                                        countersegment: Segment,
                                        countersegment_intercept: Fraction,
                                        slope: Fraction) -> Segment:
    """
    Finds splitter for parallel inclined domain and countersegment.

    Finds segment connecting parallel and non-vertical "domain"
    and "countersegment" segments so that the area on the right
    would be equal to the area requirement.

    :param area_requirement: area to the right of the splitter
        between `domain` and `countersegment`
    :param intercept_diff: `domain_intercept` minus
        `countersegment_intercept`
    :param domain: inclined segment where the splitter starts
    :param domain_intercept: intercept of the line through `domain`
    :param countersegment: inclined segment where the splitter ends,
        parallel to `domain`
    :param countersegment_intercept: intercept of the line through
        `countersegment`
    :param slope: common slope of `domain` and `countersegment`
    :return: splitter, or the segment connecting the starts
        or the ends of both segments if it lies beyond them.
    """
    tail_x = (area_requirement / intercept_diff
              + (domain.end.x + countersegment.start.x) / 2
              - slope * intercept_diff / (2 * (1 + slope ** 2)))
    if is_before_domain(tail_x, domain.start.x, domain.end.x):
        return Segment(domain.start, countersegment.start)
    if is_after_domain(tail_x, domain.start.x, domain.end.x):
        return Segment(domain.end, countersegment.end)
    tail_y = slope * tail_x + domain_intercept
    head_x = (2 * area_requirement / intercept_diff + domain.end.x
              + countersegment.start.x - tail_x)
    head_y = slope * head_x + countersegment_intercept
    tail_point = Point(tail_x, tail_y)
    head_point = Point(head_x, head_y)
    return Segment(tail_point, head_point)


def general_case_splitter(*,  # noqa: PLR0913
                          area_requirement: Fraction,
                          intercept_diff: Fraction,
                          domain: Segment,
                          domain_intercept: Fraction,
                          domain_slope: Fraction,
                          countersegment: Segment,
                          countersegment_intercept: Fraction,
                          countersegment_slope: Fraction) -> Segment:
    """
    Finds splitter for non-parallel inclined domain and countersegment.

    Finds segment connecting non-parallel and non-vertical "domain"
    and "countersegment" segments so that the area on the right
    would be equal to the area requirement.

    :param area_requirement: area to the right of the splitter
        between `domain` and `countersegment`
    :param intercept_diff: `domain_intercept` minus
        `countersegment_intercept`
    :param domain: inclined segment where the splitter starts
    :param domain_intercept: intercept of the line through `domain`
    :param domain_slope: slope of the line through `domain`
    :param countersegment: inclined segment where the splitter ends
    :param countersegment_intercept: intercept of the line through
        `countersegment`
    :param countersegment_slope: slope of the line through `countersegment`
    :return: splitter, or the segment connecting the starts
        or the ends of both segments if it lies beyond them.
    """
    slope_diff = domain_slope - countersegment_slope
    const = (2 * area_requirement
             + slope_diff * domain.end.x * countersegment.start.x
             + intercept_diff * (domain.end.x + countersegment.start.x))
    sign = (1
            if domain.start.y > countersegment_slope * domain.start.x
               + countersegment_intercept
            else -1)
    tail_x = (sign
              * fourth_root((1 + countersegment_slope ** 2)
                            / (1 + domain_slope ** 2)
                            * (intercept_diff ** 2 + slope_diff * const) ** 2)
              - intercept_diff) / slope_diff
    if is_before_domain(tail_x, domain.start.x, domain.end.x):
        return Segment(domain.start, countersegment.start)
    if is_after_domain(tail_x, domain.start.x, domain.end.x):
        return Segment(domain.end, countersegment.end)
    tail_y = tail_x * domain_slope + domain_intercept
    head_x = ((const - tail_x * intercept_diff)
              / (tail_x * slope_diff + intercept_diff))
    head_y = head_x * countersegment_slope + countersegment_intercept
    tail_point = Point(tail_x, tail_y)
    head_point = Point(head_x, head_y)
    return Segment(tail_point, head_point)


def is_before_domain(value: Fraction,
                     start: Fraction,
                     end: Fraction) -> bool:
    """
    Checks if the splitter's tail lies before the domain.

    Checks if X or Y coordinate of the segment's tail
    was found before the starting vertex of the "domain".

    :param value: coordinate of the splitter's tail
    :param start: same coordinate of the start of the domain
    :param end: same coordinate of the end of the domain
    :return: whether `value` coincides with `start` or lies
        on the opposite side of it from `end`.
    """
    return value <= start < end or value >= start > end


def is_after_domain(value: Fraction,
                    start: Fraction,
                    end: Fraction) -> bool:
    """
    Checks if the splitter's tail lies after the domain.

    Checks if X or Y coordinate of the segment's tail
    was found after the second vertex of the "domain".

    :param value: coordinate of the splitter's tail
    :param start: same coordinate of the start of the domain
    :param end: same coordinate of the end of the domain
    :return: whether `value` coincides with `end` or lies
        on the opposite side of it from `start`.
    """
    return value >= end > start or value <= end < start


def fourth_root(fraction: Fraction) -> Fraction:
    """
    Returns fourth root of the given fraction.

    Uses only integer arithmetic, so the result does not depend
    on any global state. The result is exact if the numerator
    and the denominator are perfect fourth powers. Otherwise it is
    rounded down once (not once per square root) to a multiple
    of a power of two so that it has at least `ROOT_PRECISION_BITS`
    significant bits.

    :param fraction: non-negative number to take fourth root of
    :return: fourth root of the fraction.
    :raises ValueError: if the fraction is negative.
    """
    numerator, denominator = fraction.numerator, fraction.denominator
    if numerator < 0:
        raise ValueError(f"Cannot take root of negative number: {fraction}")
    numerator_root = floor_fourth_root(numerator)
    denominator_root = floor_fourth_root(denominator)
    if (numerator_root ** 4 == numerator
            and denominator_root ** 4 == denominator):
        return Fraction(numerator_root, denominator_root)
    shift = max(0, ROOT_PRECISION_BITS
                - (numerator.bit_length() - denominator.bit_length()) // 4)
    scaled = (numerator << 4 * shift) // denominator
    return Fraction(floor_fourth_root(scaled), 1 << shift)


def floor_fourth_root(value: int) -> int:
    """
    Returns fourth root of a non-negative integer rounded down.

    For a non-negative integer `m`, `isqrt(isqrt(m))` equals the floor
    of the fourth root of `m`, so the result is rounded down only once.

    :param value: non-negative integer to take fourth root of
    :return: the largest integer whose fourth power does not exceed
        `value`.
    """
    return isqrt(isqrt(value))


def inverse_shoelace(area: Fraction,
                     endpoint: Point,
                     base_start: Point,
                     base_end: Point) -> Point:
    """
    Finds point in triangle based on inverse shoelace algorithm.

    Finds the point on the line through `base_start` and `base_end`
    such that the triangle formed by `endpoint`, `base_start`
    and that point has the given area. Coordinates of the points
    must be of `Fraction` type.

    :param area: area of the triangle to form
    :param endpoint: vertex of the triangle opposite to its base
    :param base_start: vertex of the triangle where its base starts
    :param base_end: point that sets the direction of the base
    :return: vertex of the triangle where its base ends.
    """
    orientation = Contour([endpoint, base_start, base_end]).orientation
    sign = 1 if orientation is Orientation.COUNTERCLOCKWISE else -1
    if base_end.x == base_start.x:
        numerator = 2 * area + sign * (base_start.x * base_start.y
                                       - endpoint.x * base_start.y)
        denominator = sign * (base_start.x - endpoint.x)
        y = numerator / denominator
        return Point(base_start.x, y)
    slope, intercept = slope_intercept(base_start, base_end)
    x_diff = base_start.x - endpoint.x
    numerator = 2 * area + sign * (base_start.x * endpoint.y
                                   - endpoint.x * base_start.y
                                   - intercept * x_diff)
    denominator = sign * (endpoint.y - base_start.y + slope * x_diff)
    x = numerator / denominator
    y = slope * x + intercept
    return Point(x, y)


def slope_intercept(start: Point, end: Point) -> tuple[Fraction, Fraction]:
    """
    Returns slope and intercept of the line passing through two points.

    The points must have different X coordinates.

    :param start: first point on the line
    :param end: second point on the line
    :return: slope and intercept of the line.
    """
    slope = (end.y - start.y) / (end.x - start.x)
    intercept = end.y - slope * end.x
    return slope, intercept
