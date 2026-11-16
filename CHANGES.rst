Changelog
=========

All notable changes to this project are documented in this file.
The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

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
