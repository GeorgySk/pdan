from fractions import Fraction

from gon.base import Point


def find_vertical_countersegment_end(*,
                                     domain_end: Point,
                                     countersegment_start: Point,
                                     area: Fraction) -> Point:
    dx = countersegment_start.x - domain_end.x
    signed_lower_area = dx * (domain_end.y - countersegment_start.y) / 2
    countersegment_end_y = (area - signed_lower_area) * 2 / dx + domain_end.y
    return Point(countersegment_start.x, countersegment_end_y)


def shoelace_area(*vertices: Point) -> Fraction:
    doubled_area = sum((start.x * end.y - end.x * start.y
                        for start, end in zip(vertices,
                                              [*vertices[1:], vertices[0]])),
                       start=Fraction(0))
    return abs(Fraction(doubled_area)) / 2
