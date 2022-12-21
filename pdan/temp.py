from fractions import Fraction
from itertools import chain
from typing import (Iterator,
                    List,
                    Optional,
                    Tuple)

from gon.base import (Contour,
                      Point)
from gon.base import Polygon

TRIANGULAR_CONTOUR_SIZE = 3


def discretize(contour: Contour,
               size: int) -> List[Point]:
    if size < TRIANGULAR_CONTOUR_SIZE:
        raise ValueError(f"Cannot discretize a contour into less than "
                         f"{TRIANGULAR_CONTOUR_SIZE} vertices")
    distance_delta = contour.length / size
    discretization = [contour.vertices[0]]
    accumulated_length = 0
    vertices_pairs = zip(contour.vertices,
                         chain(contour.vertices[1:], [contour.vertices[0]]))
    vertex, next_vertex = next(vertices_pairs)
    while True:
        segment_length = vertex.distance_to(next_vertex)
        accumulated_length += segment_length
        if accumulated_length < distance_delta:
            vertex, next_vertex = next(vertices_pairs)
            continue
        if accumulated_length == distance_delta:
            discretization.append(next_vertex)
            vertex, next_vertex = next(vertices_pairs)
        else:
            distance = distance_delta + segment_length - accumulated_length
            distance_fraction = distance / segment_length
            point = Point(
                vertex.x + (next_vertex.x - vertex.x) * distance_fraction,
                vertex.y + (next_vertex.y - vertex.y) * distance_fraction)
            discretization.append(point)
            vertex = point
        accumulated_length = 0
        if len(discretization) == size:
            return discretization


def divide_by_discretization(contour: Contour,
                             requirement: Fraction,
                             size: int,
                             *,
                             eps: float) -> Tuple[Contour, Contour]:
    eps *= Polygon(contour).area
    discretization = discretize(contour, size)
    min_perimeter = contour.length
    for start_index, first_vertex in enumerate(discretization):
        accumulated_vertices = [first_vertex]
        for end_index, candidate in enumerate(
                chain(discretization[start_index + 1:],
                discretization[:start_index]),
                start=start_index + 1):
            accumulated_vertices.append(candidate)
            part_contour = Contour(accumulated_vertices)
            if Polygon(part_contour).area > requirement - eps:
                part_contour_length = part_contour.length
                if part_contour_length < min_perimeter:
                    min_perimeter = part_contour_length
                    splitter_tail_index = start_index
                    splitter_head_index = end_index
                break
    if splitter_head_index < size:
        right = Contour(
            discretization[splitter_tail_index:splitter_head_index + 1])
        left = Contour(discretization[splitter_head_index:]
                       + discretization[:splitter_tail_index + 1])
    else:
        right = Contour(discretization[splitter_tail_index:]
                        + discretization[:(splitter_head_index + 1) % size])
        left = Contour(
            discretization[splitter_head_index % size:splitter_tail_index + 1])
    return right, left


def bf_multipart_split(contour: Contour,
                       requirements: List[Fraction],
                       size: int,
                       eps: float,
                       max_denominator: Optional[int] = None
                       ) -> Iterator[Contour]:
    rest = contour
    for requirement in requirements[:-1]:
        part, rest = divide_by_discretization(rest, requirement, size, eps=eps)
        if max_denominator is not None:
            part = Contour([Point(point.x.limit_denominator(max_denominator),
                                  point.y.limit_denominator(max_denominator))
                            for point in part.vertices])
            rest = Contour([Point(point.x.limit_denominator(max_denominator),
                                  point.y.limit_denominator(max_denominator))
                            for point in rest.vertices])
        yield part
    yield rest
