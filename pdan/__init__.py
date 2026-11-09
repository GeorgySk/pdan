"""Convex polygon decomposition algorithm by Skorobogatov et al., 2021."""

__author__ = "Georgy Skorobogatov"
__email__ = "skorobogatovgeorgy+github@gmail.com"
__version__ = "0.2.0"

from gon.base import (
    Contour,
    Point,
    Polygon,
    Segment,
)

from .pdan import minimizing_split

__all__ = [
    "Contour",
    "Point",
    "Polygon",
    "Segment",
    "minimizing_split",
]
