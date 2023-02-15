from fractions import Fraction
from itertools import tee

from gon.base import Point


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def find_vertical_countersegment_end(*,
                                     domain_end: Point,
                                     countersegment_start: Point,
                                     area: Fraction) -> Point:
    dx = countersegment_start.x - domain_end.x
    signed_lower_area = dx * (domain_end.y - countersegment_start.y) / 2
    countersegment_end_y = (area - signed_lower_area) * 2 / dx + domain_end.y
    return Point(countersegment_start.x, countersegment_end_y)
