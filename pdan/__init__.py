"""Implementation of the algorithm by Skorobogatov et al., 2021, for
decomposition of convex polygons.."""

__author__ = "Georgy Skorobogatov"
__email__ = "skorobogatovgeorgy+github@gmail.com"
__version__ = "0.2.0"

from .pdan import (
    Contour,
    Point,
    Polygon,
    Segment,
    minimizing_split,
)

__all__ = [
    "Contour",
    "Point",
    "Polygon",
    "Segment",
    "minimizing_split",
]
