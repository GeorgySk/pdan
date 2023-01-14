from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import (Callable,
                    Iterator,
                    List,
                    Sequence,
                    Tuple)

from gon.base import (Contour,
                      EMPTY,
                      Orientation,
                      Point,
                      Polygon,
                      Segment)
from gon.hints import Maybe


@dataclass
class Partition:
    domain: Segment
    countersegment: Segment
    right_vertices: List[Point]
    left_vertices: List[Point]
    area_difference: Fraction


def minimizing_split(contour: Contour,
                     area_requirement: Fraction,
                     *,
                     key: Callable[[Contour, Contour], Fraction]
                     ) -> Tuple[Contour, Maybe[Contour]]:
    """
    Splits convex polygon defined by the input contour,
    finds the part with the given area requirement that yields
    the minimum possible value when applied to `key` function,
    and returns it along with the remaining part as contours.
    :param contour: defines a convex polygon
    :param area_requirement: area of a part to return
    :param key: function to be applied to a pair of contours
    :return: two contours if the area requirement is not zero
    or equal to area of the polygon; one contour and empty geometry
    otherwise.
    """
    if area_requirement == Polygon(contour).area:
        return contour, EMPTY
    partitions = to_partitions(contour=contour,
                               area_requirement=area_requirement)
    min_key_value = float('inf')
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
        if key_value < min_key_value:
            min_key_contours = right_contour, left_contour
            min_key_value = key_value
    if min_key_contours is None:
        raise ValueError("Couldn't find the contour with min perimeter")
    return min_key_contours


def to_partitions(contour: Contour,
                  area_requirement: Fraction) -> Iterator[Partition]:
    """
    Returns an iterator over `Partition` objects, containing
    information about domain segments, their countersegments,
    "right" and "left" parts' vertices,
    where "right" vertices are all the original vertices
    located between the domain and countersegment when iterating
    in counterclockwise order, and left vertices are
    all the original vertices located between the countersegment and
    domain segment when iterating in counterclockwise order,
    and, finally, the area differences that should be found in the
    quadrilateral based on the domains and the countersegments.
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
            right_vertices.append(head.end)  # remove
            left_vertices.popleft()
            head = next(heads)
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
        resulting_right_vertices = (list(right_vertices)
                                    if len(right_vertices) > 2 else [])
        resulting_left_vertices = (list(left_vertices)
                                   if len(left_vertices) > 2 else [])
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
    For the given "domain" and its corresponding "countersegment",
    finds another "splitter" segment connecting these two
    so that the area on the right would be
    equal to the given area requirement
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


def to_right_left_contours(domain: Segment,
                           countersegment: Segment,
                           splitter: Segment,
                           right_vertices: List[Point],
                           left_vertices: List[Point]) -> Tuple[Contour,
                                                                Contour]:
    """
    Constructs two contours from splitter
    and vertices delimiting right and left parts
    based on the splitter's endpoints location
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
            try:
                right_vertices = right_vertices[1:]
            except TypeError:
                print("right_vertices == ", right_vertices)
                raise TypeError
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
    Finds segment connecting two vertical "domain"
    and "countersegment" segments
    so that the area on the right would be
    equal to the area requirement
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
    Finds segment connecting a vertical "domain"
    and an inclined "countersegment" segments
    so that the area on the right would be
    equal to the area requirement
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
    tail_intersection_diff_y = robust_sqrt(robust_sqrt(
        fourth_power_tail_intersection_diff_y))
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
    Finds segment connecting an inclined "domain"
    and a vertical "countersegment" segments
    so that the area on the right would be
    equal to the area requirement
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
    tail_intersection_diff_x = robust_sqrt(robust_sqrt(
        fourth_power_tail_intersection_diff_x))
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


def parallel_inclined_segments_splitter(area_requirement: Fraction,
                                        intercept_diff: Fraction,
                                        domain: Segment,
                                        domain_intercept: Fraction,
                                        countersegment: Segment,
                                        countersegment_intercept: Fraction,
                                        slope: Fraction) -> Segment:
    """
    Finds segment connecting parallel and non-vertical "domain"
    and "countersegment" segments so that the area on the right
    would be equal to the area requirement
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


def general_case_splitter(area_requirement: Fraction,
                          intercept_diff: Fraction,
                          domain: Segment,
                          domain_intercept: Fraction,
                          domain_slope: Fraction,
                          countersegment: Segment,
                          countersegment_intercept: Fraction,
                          image_slope: Fraction) -> Segment:
    """
    Finds segment connecting non-parallel and non-vertical "domain"
    and "countersegment" segments so that the area on the right
    would be equal to the area requirement
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
              * robust_sqrt((robust_sqrt((1 + image_slope ** 2)
                                         / (1 + domain_slope ** 2))
                             * abs(intercept_diff ** 2 + slope_diff * const)))
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
    Checks if X or Y coordinate of the segment's tail
    was found before the starting vertex of the "domain"
    """
    return value <= start < end or value >= start > end


def is_after_domain(value: Fraction,
                    start: Fraction,
                    end: Fraction) -> bool:
    """
    Checks if X or Y coordinate of the segment's tail
    was found after the second vertex of the "domain"
    """
    return value >= end > start or value <= end < start


def robust_sqrt(fraction: Fraction) -> Fraction:
    return Fraction((fraction.numerator
                     / Decimal(fraction.denominator)).sqrt())


def inverse_shoelace(area: Fraction,
                     endpoint: Point,
                     base_start: Point,
                     base_end: Point) -> Point:
    """
    Finds point in triangle based on inverse shoelace algorithm.
    Coordinates of the points must be of `Fraction` type.
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


def slope_intercept(start: Point, end: Point) -> Tuple[Fraction, Fraction]:
    slope = (end.y - start.y) / (end.x - start.x)
    intercept = end.y - slope * end.x
    return slope, intercept
