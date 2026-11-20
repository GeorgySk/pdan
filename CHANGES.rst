Changelog
=========

All notable changes to this project are documented in this file.
The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

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
