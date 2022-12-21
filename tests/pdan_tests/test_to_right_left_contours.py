from fractions import Fraction

from gon.base import Contour
from gon.base import Polygon
from hypothesis import given

from pdan.pdan import (to_right_left_contours,
                       to_partitions,
                       to_splitter)
from tests.strategies.base import open_interval_unit_fractions
from tests.strategies.geometry import convex_contours


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_validity(contour: Contour,
                  unit_fraction: Fraction) -> None:
    vertices = list(contour.vertices)
    polygon = Polygon(contour)
    area_requirement = unit_fraction * polygon.area
    partition = next(to_partitions(vertices, area_requirement))
    splitter = to_splitter(domain=partition.domain,
                           countersegment=partition.countersegment,
                           area_requirement=partition.area_difference)
    right_contour, left_contour = to_right_left_contours(
        domain=partition.domain,
        countersegment=partition.countersegment,
        splitter=splitter,
        right_vertices=partition.right_vertices,
        left_vertices=partition.left_vertices)
    right_contour.validate()
    left_contour.validate()


@given(contour=convex_contours,
       unit_fraction=open_interval_unit_fractions)
def test_parts_inclusion(contour: Contour,
                         unit_fraction: Fraction) -> None:
    vertices = list(contour.vertices)
    polygon = Polygon(contour)
    area_requirement = unit_fraction * polygon.area
    partition = next(to_partitions(vertices, area_requirement))
    splitter = to_splitter(domain=partition.domain,
                           countersegment=partition.countersegment,
                           area_requirement=partition.area_difference)
    right_contour, left_contour = to_right_left_contours(
        domain=partition.domain,
        countersegment=partition.countersegment,
        splitter=splitter,
        right_vertices=partition.right_vertices,
        left_vertices=partition.left_vertices)
    assert ((splitter < right_contour) and (splitter < left_contour)
            and (Polygon(right_contour) <= polygon)
            and (Polygon(left_contour) <= polygon))
