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
    min_key_value: KeyValue | None = None
    min_key_contours = None
    for partition in partitions:
        splitter = to_splitter(domain=partition.domain,
                               countersegment=partition.countersegment,
                               area_requirement=partition.area_difference)
        right_contour, left_contour = to_right_left_contours(
            domain=partition.domain,
            countersegment=partition.countersegment,
            splitter=splitter,
            right_vertices=partition.right_vertices,
            left_vertices=partition.left_vertices)
        key_value = key(right_contour, left_contour)
        if min_key_value is None or key_value < min_key_value:
            min_key_contours = right_contour, left_contour
            min_key_value = key_value
    if min_key_contours is None:
        raise ValueError("Couldn't find any split of the polygon.")
    return min_key_contours


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
    :raises ValueError: if no countervertex is found for the first
        domain, which does not happen for a valid area requirement.
    """
    segments = contour.segments
    # in gon, the last segment goes first, the first one goes second, and so on
    tails = iter([*segments[1:], segments[0]])
    heads = iter([*segments[2:], *segments])
    tail = next(tails)
    accumulated_area = 0
    right_vertices = deque([tail.start])
    left_vertices = deque(contour.vertices[1:])
    for head in heads:
        right_vertices.append(head.start)
        left_vertices.popleft()
        covered_triangle_area = Polygon(Contour([tail.start,
                                                 head.start,
                                                 head.end])).area
        accumulated_area += covered_triangle_area
        if accumulated_area < area_requirement:
            continue
        elif accumulated_area == area_requirement:
            right_vertices.append(head.end)
            left_vertices.popleft()
            head = next(heads)  # noqa: PLW2901
            countervertex = head.start
            is_head_based_on_original_vertex = True
        else:
            area = covered_triangle_area + area_requirement - accumulated_area
            countervertex = inverse_shoelace(area=area,
                                             endpoint=tail.start,
                                             base_start=head.start,
                                             base_end=head.end)
            right_vertices.append(countervertex)
            is_head_based_on_original_vertex = False
        break
    else:
        raise ValueError("Couldn't find countervertex.")
    is_tail_start_original = True
    while True:
        tail_based_triangle_area = Polygon(Contour([tail.start,
                                                    tail.end,
                                                    countervertex])).area
        head_based_triangle_area = Polygon(Contour([tail.end,
                                                    countervertex,
                                                    head.end])).area
        right_vertices.popleft()
        left_vertices.append(tail.start)
        if tail_based_triangle_area == head_based_triangle_area:
            domain = tail
            domain_based_area = tail_based_triangle_area
            image_end = head.end
            tail = next(tails, None)
            head = next(heads)
        elif head_based_triangle_area > tail_based_triangle_area:
            domain = tail
            domain_based_area = tail_based_triangle_area
            image_end = inverse_shoelace(area=tail_based_triangle_area,
                                         endpoint=tail.end,
                                         base_start=countervertex,
                                         base_end=head.end)
            left_vertices.appendleft(image_end)
            tail = next(tails, None)
            head = Segment(image_end, head.end)
        else:
            area_difference = (tail_based_triangle_area
                               - head_based_triangle_area)
            domain_end = inverse_shoelace(area=area_difference,
                                          endpoint=head.end,
                                          base_start=tail.end,
                                          base_end=tail.start)
            right_vertices.appendleft(domain_end)
            domain = Segment(tail.start, domain_end)
            domain_based_area = Polygon(Contour([domain.start,
                                                 domain.end,
                                                 countervertex])).area
            image_end = head.end
            tail = Segment(domain_end, tail.end)
            head = next(heads)
        countersegment = Segment(countervertex, image_end)
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
        if tail is None:
            return
        countervertex = head.start
        if not is_head_based_on_original_vertex:
            right_vertices.pop()
        if not is_tail_start_original:
            left_vertices.pop()
        right_vertices.append(countervertex)
        left_vertices.popleft()
        is_head_based_on_original_vertex = (head_based_triangle_area
                                            <= tail_based_triangle_area)
        is_tail_start_original = (head_based_triangle_area
                                  >= tail_based_triangle_area)


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
        image_slope=countersegment_slope)


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
    domain_image_intersection_y = slope * domain.end.x + intercept
    const = (2 * area_requirement
             - domain_image_intersection_y * countersegment.start.x
             + domain.end.y * (countersegment.start.x - domain.end.x))
    fourth_power_tail_intersection_diff_y = (
            (domain_image_intersection_y * domain.end.x + const) ** 2
            * (1 + slope ** 2))
    sign = 1 if domain_image_intersection_y < domain.end.y else -1
    tail_intersection_diff_y = fourth_root(
        fourth_power_tail_intersection_diff_y)
    tail_y = (Fraction(sign * tail_intersection_diff_y)
              + domain_image_intersection_y)
    if is_before_domain(tail_y, domain.start.y, domain.end.y):
        return Segment(domain.start, countersegment.start)
    if is_after_domain(tail_y, domain.start.y, domain.end.y):
        return Segment(domain.end, countersegment.end)
    head_x = ((const + domain.end.x * tail_y)
              / (tail_y - domain_image_intersection_y))
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
    domain_image_intersection_y = slope * countersegment.start.x + intercept
    fourth_power_tail_intersection_diff_x = (
            (const - domain_image_intersection_y * countersegment.start.x) ** 2
            / (1 + slope ** 2))
    sign = 1 if domain.start.x > countersegment.end.x else -1
    tail_intersection_diff_x = fourth_root(
        fourth_power_tail_intersection_diff_x)
    tail_x = Fraction(countersegment.start.x + sign * tail_intersection_diff_x)
    if is_before_domain(tail_x, domain.start.x, domain.end.x):
        return Segment(domain.start, countersegment.start)
    if is_after_domain(tail_x, domain.start.x, domain.end.x):
        return Segment(domain.end, countersegment.end)
    tail_y = tail_x * slope + intercept
    head_y = ((const - tail_x * domain_image_intersection_y)
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
                          image_slope: Fraction) -> Segment:
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
    :param image_slope: slope of the line through `countersegment`
    :return: splitter, or the segment connecting the starts
        or the ends of both segments if it lies beyond them.
    """
    slope_diff = domain_slope - image_slope
    const = (2 * area_requirement
             + slope_diff * domain.end.x * countersegment.start.x
             + intercept_diff * (domain.end.x + countersegment.start.x))
    sign = (1
            if domain.start.y > image_slope * domain.start.x
               + countersegment_intercept
            else -1)
    tail_x = (sign
              * fourth_root((1 + image_slope ** 2)
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
    head_y = head_x * image_slope + countersegment_intercept
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


def robust_sqrt(fraction: Fraction) -> Fraction:
    """
    Returns square root of the given fraction.

    The result is exact if the numerator and the denominator
    are perfect squares. Otherwise it is rounded down to a multiple
    of a power of two so that it has at least `ROOT_PRECISION_BITS`
    significant bits. The result does not depend on any global state.

    :param fraction: non-negative number to take square root of
    :return: square root of the fraction.
    """
    return _integer_root(fraction, 2)


def fourth_root(fraction: Fraction) -> Fraction:
    """
    Returns fourth root of the given fraction.

    The result is exact if the numerator and the denominator
    are perfect fourth powers. Otherwise it is rounded down once
    (not once per square root) to a multiple of a power of two
    so that it has at least `ROOT_PRECISION_BITS` significant bits.

    :param fraction: non-negative number to take fourth root of
    :return: fourth root of the fraction.
    """
    return _integer_root(fraction, 4)


def _integer_root(fraction: Fraction,
                  degree: int) -> Fraction:
    """
    Returns root of the given fraction of degree two or four.

    Uses only integer arithmetic. For a non-negative integer `m`,
    `isqrt(isqrt(m))` equals the floor of the fourth root of `m`,
    so the fourth root is rounded down only once.

    :param fraction: non-negative number to take root of
    :param degree: degree of the root, either 2 or 4
    :return: exact root if both the numerator and the denominator
        are perfect powers of `degree`, the root rounded down
        to a multiple of a power of two otherwise.
    :raises ValueError: if the fraction is negative.
    """
    numerator, denominator = fraction.numerator, fraction.denominator
    if numerator < 0:
        raise ValueError(f"Cannot take root of negative number: {fraction}")
    numerator_root = _floor_root(numerator, degree)
    denominator_root = _floor_root(denominator, degree)
    if (numerator_root ** degree == numerator
            and denominator_root ** degree == denominator):
        return Fraction(numerator_root, denominator_root)
    shift = max(0, ROOT_PRECISION_BITS
                - (numerator.bit_length() - denominator.bit_length())
                // degree)
    scaled = (numerator << degree * shift) // denominator
    return Fraction(_floor_root(scaled, degree), 1 << shift)


def _floor_root(value: int,
                degree: int) -> int:
    """
    Returns root of a non-negative integer rounded down.

    :param value: non-negative integer to take root of
    :param degree: degree of the root, a power of two
    :return: the largest integer whose power of `degree`
        does not exceed `value`.
    """
    root = value
    while degree > 1:
        root = isqrt(root)
        degree //= 2
    return root


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
    if base_end.x - base_start.x == 0:
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
