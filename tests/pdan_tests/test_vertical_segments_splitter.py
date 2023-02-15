from __future__ import annotations
from fractions import Fraction

from gon.base import Segment
from hypothesis import given

from pdan.pdan import vertical_segments_splitter
from tests.strategies.geometry import vertical_ccw_segments_and_areas


@given(vertical_ccw_segments_and_areas)
def test_connection(vertical_ccw_segments_pair: tuple[Segment[Fraction],
                                                      Segment[Fraction],
                                                      Fraction]
                    ) -> None:
    domain, countersegment, area_requirement = vertical_ccw_segments_pair
    connector = vertical_segments_splitter(area_requirement,
                                           domain,
                                           countersegment)
    assert connector.start in domain
    assert connector.end in countersegment
