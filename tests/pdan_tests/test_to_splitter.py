from typing import Tuple

from gon.base import (Contour,
                        Segment)
from gon.base import Polygon
from hypothesis import (example,
                        given)

from pdan.pdan import to_splitter
from tests.strategies.geometry import countersegments_pairs


@given(countersegments_pair=countersegments_pairs)
def test_endpoints_location(countersegments_pair: Tuple[Segment, Segment]
                            ) -> None:
    domain, countersegment = countersegments_pair
    area_requirement = Polygon(Contour([domain.start, domain.end,
                                        countersegment.start])).area
    splitter = to_splitter(domain=domain,
                           countersegment=countersegment,
                           area_requirement=area_requirement)
    assert splitter.start in domain and splitter.end in countersegment


@given(countersegments_pairs=countersegments_pairs)
def test_area(countersegments_pairs: Tuple[Segment, Segment]) -> None:
    domain, countersegment = countersegments_pairs
    area_requirement = Polygon(Contour([domain.start, domain.end,
                                        countersegment.start])).area
    splitter = to_splitter(domain=domain,
                           countersegment=countersegment,
                           area_requirement=area_requirement)
    starting_splitter = Segment(domain.start, countersegment.start)
    final_splitter = Segment(domain.end, countersegment.end)
    if splitter not in {starting_splitter, final_splitter}:
        assert Polygon(Contour([splitter.start,
                                domain.end,
                                countersegment.start,
                                splitter.end])).area == area_requirement


@given(countersegments_pairs=countersegments_pairs)
def test_perimeter_inequalities(countersegments_pairs: Tuple[Segment, Segment]
                                ) -> None:
    domain, countersegment = countersegments_pairs
    area_requirement = Polygon(Contour([domain.start, domain.end,
                                        countersegment.start])).area
    splitter = to_splitter(domain=domain,
                           countersegment=countersegment,
                           area_requirement=area_requirement)
    squared_splitter_length = ((splitter.start.x - splitter.end.x) ** 2
                               + (splitter.start.y - splitter.end.y) ** 2)
    squared_starting_splitter_length = (
            (domain.start.x - countersegment.start.x) ** 2
            + (domain.start.y - countersegment.start.y) ** 2)
    squared_final_splitter_length = (
            (domain.end.x - countersegment.end.x) ** 2
            + (domain.end.y - countersegment.end.y) ** 2)
    assert squared_splitter_length <= min(squared_starting_splitter_length,
                                          squared_final_splitter_length)
