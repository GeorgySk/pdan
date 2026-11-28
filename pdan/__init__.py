"""Convex polygon decomposition algorithm by Skorobogatov et al., 2021."""

__author__ = "Georgy Skorobogatov"
__email__ = "skorobogatovgeorgy+github@gmail.com"
__version__ = "0.2.5"

from gon.base import (
    Contour,
    Point,
    Polygon,
    Segment,
)

from .pdan import (
    minimizing_decomposition,
    minimizing_split,
)
from .radicals import (
    RadicalSum,
    perimeter,
)

__all__ = [
    "Contour",
    "Point",
    "Polygon",
    "RadicalSum",
    "Segment",
    "minimizing_decomposition",
    "minimizing_split",
    "perimeter",
]
