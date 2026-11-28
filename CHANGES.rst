Changelog
=========

All notable changes to this project are documented in this file.
The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

Added
~~~~~

- ``minimizing_decomposition`` divides a convex polygon into any number
  of parts with given areas, cutting them off one at a time from the largest
  area to the smallest. By default, the ends of each cut are rounded
  to ``precision_bits=96`` bits along their edges, which keeps the sizes
  of the coordinates growing linearly with the number of parts instead
  of exponentially; ``precision_bits=None`` keeps the areas exact.
- ``perimeter`` returns the exact perimeter of a contour as a ``RadicalSum``,
  an exact sum of products of square roots of rationals. It compares by
  bounding both sides with integer arithmetic and falls back to exact
  computations only if the bounds overlap, so as a ``key`` it runs about
  as fast as a float key. ``Contour.length`` is just as exact, but becomes
  too slow, or exceeds Python's limit on integer string conversion,
  after a few cuts of ``minimizing_decomposition`` with exact areas.

0.2.5 (2026-11-23)
------------------------------

Changed
~~~~~~~

- ``minimizing_split`` now raises ``ValueError`` if the contour doesn't
  define a non-degenerate convex polygon: if it has fewer than three
  vertices, three consecutive vertices on one line (including repeated
  ones), self-intersections or a reflex angle. Such contours used to give
  parts with a wrong area, or fail with unrelated errors. Contours with
  collinear consecutive vertices used to work and are now rejected too,
  following ``gon``'s definition of a valid contour.
- All contours returned by ``minimizing_split`` are now counterclockwise.

Fixed
~~~~~

- Clockwise contours used to give non-optimal splits, and sometimes parts
  with a wrong area.

0.2.4 (2026-11-20)
------------------------------

Changed
~~~~~~~

- ``key`` in ``minimizing_split`` may now return any values that support
  comparison with ``<`` (e.g. ``float``, ``int`` or tuples), not only
  ``Fraction``. This only affects type checking.

0.2.3 (2026-11-18)
------------------------------

Changed
~~~~~~~

- Square and fourth roots in splitters are now computed with ``math.isqrt``
  instead of ``Decimal``. Coordinates of splitter endpoints may differ
  slightly from 0.2.2; areas of the parts are still exact.

Fixed
~~~~~

- ``minimizing_split`` no longer depends on the global ``decimal`` context,
  so the same input always gives the same split.
- Roots of perfect squares and perfect fourth powers are now exact.

0.2.2 (2026-11-16)
------------------------------

Changed
~~~~~~~

- ``minimizing_split`` now returns ``tuple[Maybe[Contour], Maybe[Contour]]``:
  for a zero area requirement, the first element is ``EMPTY`` and
  the second one is the input contour, as documented.

Fixed
~~~~~

- ``minimizing_split`` now raises ``ValueError`` when the area requirement
  is negative or exceeds the area of the polygon, instead of returning
  a wrong part or failing with ``IndexError``.
- ``minimizing_split`` no longer returns a degenerate contour with zero area
  for a zero area requirement.

0.2.1 (2026-11-12)
------------------------------
