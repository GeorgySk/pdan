from numbers import Real

from gon.base import (Contour,
                        Segment)
from gon.base import Polygon
from hypothesis import given

from pdan.pdan import inverse_shoelace
from tests.strategies.base import open_interval_unit_fractions
from tests.strategies.geometry import triangle_contours


@given(triangle_contour=triangle_contours,
       unit_fraction=open_interval_unit_fractions)
def test_boundary_inclusion(triangle_contour: Contour,
                            unit_fraction: Real) -> None:
    area_requirement = unit_fraction * Polygon(triangle_contour).area
    endpoint, base_start, base_end = triangle_contour.vertices
    point = inverse_shoelace(area=area_requirement,
                             endpoint=endpoint,
                             base_start=base_start,
                             base_end=base_end)
    assert point in Segment(base_start, base_end)


@given(triangle_contours)
def test_endpoints(triangle_contour: Contour) -> None:
    endpoint, base_start, base_end = triangle_contour.vertices
    point = inverse_shoelace(area=0,
                             endpoint=endpoint,
                             base_start=base_start,
                             base_end=base_end)
    assert point == base_start
    point = inverse_shoelace(area=Polygon(triangle_contour).area,
                             endpoint=endpoint,
                             base_start=base_start,
                             base_end=base_end)
    assert point == base_end
