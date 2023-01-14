from fractions import Fraction

from gon.base import (Point,
                      Relation)
from gon.base import (Contour,
                        Segment)
from gon.base import Polygon
from hypothesis import (Verbosity,
                        example,
                        given,
                        settings)

from pdan.pdan import to_partitions
from tests.pdan_tests.utils import pairwise
from tests.strategies.base import open_interval_unit_fractions
from tests.strategies.geometry import convex_contours


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_domains_and_images_disjoint(contour: Contour,
                                     unit_fraction: Fraction) -> None:
    area_requirement = unit_fraction * Polygon(contour).area
    partitions = to_partitions(contour, area_requirement)
    assert all(
        partition.domain.relate(partition.countersegment) is Relation.DISJOINT
        for partition in partitions)


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_segments_lengths(contour: Contour,
                          unit_fraction: Fraction) -> None:
    area_requirement = unit_fraction * Polygon(contour).area
    partitions = to_partitions(contour, area_requirement)
    assert all(partition.domain.length > 0
               and partition.countersegment.length > 0
               for partition in partitions)


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_contours_validity(contour: Contour,
                           unit_fraction: Fraction) -> None:
    area_requirement = unit_fraction * Polygon(contour).area
    partitions = to_partitions(contour, area_requirement)
    for partition in partitions:
        if partition.right_vertices:
            Contour(partition.right_vertices).validate()
        if partition.left_vertices:
            Contour(partition.left_vertices).validate()


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_consecutive(contour: Contour,
                     unit_fraction: Fraction) -> None:
    area_requirement = unit_fraction * Polygon(contour).area
    partitions = to_partitions(contour, area_requirement)
    assert all(
        partition.domain.end == next_partition.domain.start
        and partition.countersegment.end == next_partition.countersegment.start
        for partition, next_partition in pairwise(partitions))


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_vertices_connection_with_segments(contour: Contour,
                                           unit_fraction: Fraction
                                           ) -> None:
    area_requirement = unit_fraction * Polygon(contour).area
    partitions = to_partitions(contour, area_requirement)
    for partition in partitions:
        if partition.right_vertices:
            assert (partition.domain.end == partition.right_vertices[0]
                    and partition.right_vertices[-1]
                    == partition.countersegment.start)
        if partition.left_vertices:
            assert (partition.countersegment.end == partition.left_vertices[0]
                    and partition.left_vertices[-1] == partition.domain.start)


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_inclusion(contour: Contour,
                   unit_fraction: Fraction) -> None:
    polygon = Polygon(contour)
    area_requirement = unit_fraction * polygon.area
    partitions = to_partitions(contour, area_requirement)
    assert all(
        partition.domain < contour and partition.countersegment < contour
        and (Polygon(Contour(partition.right_vertices)) <= polygon
             if partition.right_vertices
             else Segment(partition.domain.end,
                          partition.countersegment.start) < contour)
        and (Polygon(Contour(partition.left_vertices)) <= polygon
             if partition.left_vertices
             else Segment(partition.countersegment.end,
                          partition.domain.start) < contour)
        for partition in partitions)


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
@settings(verbosity=Verbosity.verbose)
def test_area_diff_range(contour: Contour,
                         unit_fraction: Fraction) -> None:
    polygon = Polygon(contour)
    area_requirement = unit_fraction * polygon.area
    partitions = to_partitions(contour, area_requirement)
    assert all(0 < partition.area_difference <= area_requirement
               for partition in partitions)


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
@example(contour=Contour([Point(Fraction(-1, 1), Fraction(0, 1)),
                       Point(Fraction(0, 1), Fraction(-1, 2)),
                       Point(Fraction(1, 2), Fraction(0, 1)),
                       Point(Fraction(0, 1), Fraction(1, 2))]),
         unit_fraction=Fraction(1, 2))
def test_sum_with_right_vertices(contour: Contour,
                                 unit_fraction: Fraction) -> None:
    polygon = Polygon(contour)
    area_requirement = unit_fraction * polygon.area
    partitions = to_partitions(contour, area_requirement)
    assert all(area_requirement == partition.area_difference
               + (Polygon(Contour(partition.right_vertices)).area
                  if partition.right_vertices else 0)
               for partition in partitions)


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_total_area_of_all_parts(contour: Contour,
                                 unit_fraction: Fraction) -> None:
    vertices = list(contour.vertices)
    polygon = Polygon(contour)
    area_requirement = unit_fraction * polygon.area
    partitions_iterators = [to_partitions(contour, area_requirement)]
    # the following cases are too hard to generate
    for index in range(2, len(vertices) - 2):
        requirement = Polygon(Contour(vertices[:index + 1])).area
        partitions_iterators.append(to_partitions(contour, requirement))
    for partitions in partitions_iterators:
        assert all(
            polygon.area == (
                    (Polygon(Contour(partition.right_vertices)).area
                     if partition.right_vertices else 0)
                    + (Polygon(Contour(partition.left_vertices)).area
                       if partition.left_vertices else 0)
                    + Polygon(Contour([partition.domain.start,
                                       partition.domain.end,
                                       partition.countersegment.start,
                                       partition.countersegment.end])).area)
            for partition in partitions)
