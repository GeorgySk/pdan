from fractions import Fraction

from gon.base import (
    Contour,
    Orientation,
    Point,
    Polygon,
    Segment,
)
from hypothesis import (
    example,
    given,
)

from pdan.pdan import (
    round_split,
    validate_convex_contour,
)
from tests.strategies.geometry import (
    collapsing_splits,
    split_precisions,
    splits,
)

Split = tuple[Contour, Contour, Contour]

TRIANGLE = Contour([Point(0, 0), Point(4, 0), Point(0, 4)])
CORNER_SPLIT = (TRIANGLE,
                Contour([Point(0, 0), Point(3, 0), Point(0, 3)]),
                Contour([Point(3, 0), Point(4, 0), Point(0, 4),
                         Point(0, 3)]))


def to_edge_position(contour: Contour, point: Point) -> Fraction | None:
    vertices = contour.vertices
    for index, start in enumerate(vertices):
        end = vertices[(index + 1) % len(vertices)]
        if point in Segment(start, end):
            position: Fraction = (
                Fraction(point.x - start.x) / (end.x - start.x)
                if start.x != end.x
                else Fraction(point.y - start.y) / (end.y - start.y))
            return position
    return None


@given(split=splits,
       precision_bits=split_precisions)
@example(split=CORNER_SPLIT, precision_bits=1)
def test_part_shrinks(split: Split, precision_bits: int) -> None:
    contour, part, rest = split
    rounded_part, rounded_rest = round_split(contour, part, rest,
                                             precision_bits=precision_bits)
    assert Polygon(rounded_part).area <= Polygon(part).area
    assert (Polygon(rounded_part).area + Polygon(rounded_rest).area
            == Polygon(contour).area)


@given(split=splits,
       precision_bits=split_precisions)
@example(split=CORNER_SPLIT, precision_bits=1)
def test_union(split: Split, precision_bits: int) -> None:
    contour, part, rest = split
    rounded_part, rounded_rest = round_split(contour, part, rest,
                                             precision_bits=precision_bits)
    union = Polygon(rounded_part) | Polygon(rounded_rest)
    assert isinstance(union, Polygon)
    assert union.border == contour


@given(split=splits,
       precision_bits=split_precisions)
def test_parts_are_valid(split: Split, precision_bits: int) -> None:
    contour, part, rest = split
    rounded_part, rounded_rest = round_split(contour, part, rest,
                                             precision_bits=precision_bits)
    validate_convex_contour(rounded_part)
    validate_convex_contour(rounded_rest)
    assert rounded_part.orientation is Orientation.COUNTERCLOCKWISE
    assert rounded_rest.orientation is Orientation.COUNTERCLOCKWISE


@given(split=splits,
       precision_bits=split_precisions)
@example(split=CORNER_SPLIT, precision_bits=1)
def test_positions(split: Split, precision_bits: int) -> None:
    contour, part, rest = split
    rounded_part, rounded_rest = round_split(contour, part, rest,
                                             precision_bits=precision_bits)
    if (rounded_part, rounded_rest) == (part, rest):
        # left exact
        return
    vertices = set(contour.vertices)
    for vertex in rounded_part.vertices:
        if vertex in vertices:
            continue
        position = to_edge_position(contour, vertex)
        assert position is not None
        assert (position * (1 << precision_bits)).denominator == 1


@given(collapsing_split=collapsing_splits)
@example(collapsing_split=(
    TRIANGLE,
    Contour([Point(0, 0), Point(1, 0), Point(0, 1)]),
    Contour([Point(1, 0), Point(4, 0), Point(0, 4), Point(0, 1)]),
    1))
def test_collapsing_part_is_left_exact(
        collapsing_split: tuple[Contour, Contour, Contour, int]
) -> None:
    contour, part, rest, precision_bits = collapsing_split
    assert round_split(contour, part, rest,
                       precision_bits=precision_bits) == (part, rest)
