pdan
===

[![](https://github.com/GeorgySk/pdan/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/GeorgySk/pdan/actions/workflows/ci.yml?query=branch%3Amain "GitHub Actions")
[![](https://codecov.io/gh/GeorgySk/pdan/branch/main/graph/badge.svg)](https://codecov.io/gh/GeorgySk/pdan "Codecov")
[![](https://readthedocs.org/projects/pdan/badge/?version=latest)](https://pdan.readthedocs.io/en/latest "Documentation")
[![](https://img.shields.io/github/license/GeorgySk/pdan.svg)](https://github.com/GeorgySk/pdan/blob/main/LICENSE "License")
[![](https://badge.fury.io/py/pdan.svg)](https://badge.fury.io/py/pdan "PyPI")
[![](https://img.shields.io/pypi/pyversions/pdan.svg)](https://pypi.org/project/pdan "Supported Python versions")
[![](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-orange.json)](https://github.com/GeorgySk/copier-pypackage "Generated from the copier-pypackage template")

Summary
-------

`pdan` is a Python library that implements the algorithm of
[Skorobogatov, G. et al., 2021](https://ieeexplore.ieee.org/abstract/document/9646907)
for dividing a convex polygon into parts with given areas, for example
to divide a workspace among several robots.

- `minimizing_split` cuts off one part with a given area, choosing the cut
  that minimizes a user-supplied `key` function, such as the perimeter
  of the part.
- `minimizing_decomposition` divides the polygon into any number of parts
  by cutting them off one at a time, from the largest area to the smallest.

Arithmetic is exact, and all parts are convex.

---

In what follows, `python` is an alias for `python3.11`
or any later version.

Installation
------------

Install the latest `pip` & `setuptools` packages versions
```bash
python -m pip install --upgrade pip setuptools
```

### User

Download and install the latest stable version from `PyPI` repository
```bash
python -m pip install --upgrade pdan
```

### Developer

Download the latest version from `GitHub` repository
```bash
git clone https://github.com/GeorgySk/pdan.git
cd pdan
```

Install
```bash
poetry install
```

Usage
-----

```python
>>> from fractions import Fraction
>>> from pdan import minimizing_split, Contour, Point, Polygon
>>> contour = Contour([Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)])
>>> part, other = minimizing_split(contour, Fraction(1, 2),
...                                key=lambda x, y: x.length)
>>> Polygon(part).area == Polygon(other).area == Fraction(1, 2)
True

```

All computations are exact. Integer and float inputs are converted
to `Fraction`s, floats to the exact binary value they store:
`0.1` becomes `3602879701896397/36028797018963968`, not `1/10`.
To work with exact decimal values, pass `Fraction`s, for example
`Fraction("0.1")`:

```python
>>> part, _ = minimizing_split(contour, 0.1, key=lambda x, y: x.length)
>>> Polygon(part).area == 0.1
True
>>> Polygon(part).area == Fraction(1, 10)
False
>>> part, _ = minimizing_split(contour, Fraction("0.1"),
...                           key=lambda x, y: x.length)
>>> Polygon(part).area == Fraction(1, 10)
True

```

`minimizing_split` returns the part with the requested area first and the
rest of the polygon second, both counterclockwise. `key` receives them in the
same order, and its values only need to support comparison with `<`.
An area requirement of zero gives empty geometry and the polygon,
one equal to the area of the polygon gives the polygon and empty geometry.
A negative requirement, one larger than the area of the polygon,
or a contour that doesn't define a convex polygon raise `ValueError`.

`key` chooses among the splits that are shortest between each pair of edges
of the polygon, so it is meant for perimeter-like functions:
other functions may not reach their minimum over all possible splits.

### Decomposition into multiple parts

`minimizing_decomposition` returns one part per area requirement, in the same
order, with empty geometry for zero requirements. The requirements must sum
exactly to the area of the polygon.

Each cut depends on the previous ones, so exact coordinates grow exponentially
with the number of parts. By default, the ends of each cut are therefore
rounded to 96 bits along their edges: the parts still cover the polygon
exactly, but their areas may differ from the requirements by a tiny amount
(at most `2 ** (1 - precision_bits)` times the squared diameter of the
polygon). Pass `precision_bits=None` for exact areas, which is practical only
for a few parts.

Exact perimeters (`Contour.length`) get slow to compare as the parts gain
vertices, so use a float key such as:

```python
>>> from math import hypot
>>> from pdan import minimizing_decomposition
>>> def perimeter(part, _rest):
...     return sum(hypot(segment.end.x - segment.start.x,
...                      segment.end.y - segment.start.y)
...                for segment in part.segments)
>>> requirements = [Fraction(1, 6), Fraction(1, 2), Fraction(1, 3)]
>>> parts = minimizing_decomposition(contour, requirements, key=perimeter,
...                                  precision_bits=None)
>>> [Polygon(part).area for part in parts] == requirements
True
>>> parts = minimizing_decomposition(contour, requirements, key=perimeter)
>>> all(abs(Polygon(part).area - requirement) < Fraction(1, 2 ** 90)
...     for part, requirement in zip(parts, requirements))
True
>>> sum(Polygon(part).area for part in parts)
Fraction(1, 1)

```

Development
-----------

### Bumping version

#### Preparation

Install
[bump-my-version](https://github.com/callowayproject/bump-my-version/tree/master?tab=readme-ov-file#installation).

#### Pre-release

Choose which version number category to bump following [semver
specification](http://semver.org/).

Test bumping version
```bash
bump-my-version bump --dry-run --verbose $CATEGORY
```

where `$CATEGORY` is the target version number category name, possible
values are `patch`/`minor`/`major`.

Bump version
```bash
bump-my-version bump --verbose $CATEGORY
```

This will set version to `major.minor.patch-alpha`. 

#### Release

Test bumping version
```bash
bump-my-version bump --dry-run --verbose release
```

Bump version
```bash
bump-my-version bump --verbose release
```

This will set version to `major.minor.patch`.

### Continuous integration

To save CI minutes, the checks (linting, tests, docs and package build) don't
run on every push:

- Pull requests: every check, with the tests on the oldest and newest
  supported Python. Draft pull requests run nothing, so open a pull request
  as a draft while working on it and mark it ready for review to run CI.
  On GitHub, a new push cancels the run for the previous one.
- The default branch: only the tests on the oldest Python, for the coverage
  report and the badges. The merged changes were checked in their pull
  request.
- Final release tags `vX.Y.Z`: every check, with the tests on every supported
  Python, then publishing (see below). Pre-release tags `vX.Y.Z-alpha` run
  nothing.

Every job has a timeout, so a hanging test can't use up the minutes.
Dependabot opens its pull requests monthly, one per ecosystem (major
updates of Python dependencies apart).

Since a merge is followed by only some of the tests, don't merge a pull
request unless its last commit passed CI.
On GitHub, enforce this with a ruleset (Settings → Rules → Rulesets → New
branch ruleset) that targets the default branch and has "Require status
checks to pass" with the `ci-passed` check, the job that passes only when
every other check did. Leave "Require branches to be up to date before
merging" off: it reruns CI every time the default branch moves. Rulesets
are available for public repositories on every plan, but for private ones
only on paid plans (GitHub Pro, Team or Enterprise).

### Publishing

Pushing a final release tag `vX.Y.Z` runs the CI publish jobs, which upload
the package to PyPI and push
the `prod` Docker image to the GitHub container registry (GHCR).
Pre-release tags such as `vX.Y.Z-alpha` are not published.
Alongside them, once the checks pass, the `release` job creates a GitHub release
for the tag, with the version's section of `CHANGES.rst` as its notes, so
add the changelog entries before bumping. It doesn't wait for the publish
jobs: if one fails, fix the cause and re-run that job (not the whole
pipeline, since a version can be uploaded to PyPI only once).

Release from the default branch once the changes are merged, so that what is
published has been reviewed and tested.
`bump-my-version bump release` commits and tags the release, so push both:
```bash
git push --follow-tags
```
A plain `git push` doesn't push tags. To make it push the tags of the commits
it pushes, run once
```bash
git config --global push.followTags true
```

One-time setup:

- GitHub: on PyPI, add a
  [Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
  for this repository with workflow `ci.yml` and environment `pypi`.
- GitHub: add a `CODECOV_TOKEN` repository secret from
  [Codecov](https://codecov.io/).

### Linting, formatting and type checking

[Ruff](https://docs.astral.sh/ruff/) is used for linting
(installed with the `dev` dependency group).

Check code
```bash
ruff check .
```

Fix automatically fixable issues
```bash
ruff check --fix .
```

[mypy](https://mypy.readthedocs.io/) checks types in strict mode
(configured in `pyproject.toml`)
```bash
mypy .
```

The package ships a `py.typed` marker, so projects that use it get its type
hints too.

To run these checks (Ruff and mypy) automatically on each commit,
install the [pre-commit](https://pre-commit.com/) hooks
(once, after the repository has been initialized with `git init`)
```bash
pre-commit install
```

### Running tests

Install the project with the `dev` dependency group (pytest, pytest-cov,
Hypothesis)
```bash
poetry install --with dev
```

Run the tests
```bash
poetry run pytest
```

Run the tests with a coverage report, as CI does
```bash
poetry run pytest --cov --cov-report=term
```

Inside the dev container, dependencies are already installed into the
container's Python, so `poetry run` can be dropped: `pytest`.

Inside a `Docker` container (the default `IMAGE_TYPE=dev` image includes the
`dev` group)
```bash
docker compose run --rm --entrypoint pytest pdan
```

### Updating from the template

This project was generated from the
[copier-pypackage](https://github.com/GeorgySk/copier-pypackage) template.
To pull in a newer release of the template (CI, tooling and configuration
fixes), commit your changes, then run
```bash
poetry run copier update --defaults
```
Copier is in the `dev` dependency group, so there is nothing else to install
(in an environment where Poetry installs into the active Python, such as the
dev container, plain `copier update --defaults` works too).
Copier merges the template's changes into the project and keeps yours.
Review them with `git diff`, resolve any conflict markers and commit.
`CHANGES.rst` and `pdan/__init__.py` are never touched by
updates, and `.copier-answers.yml` must not be edited by hand.

The `Template update` workflow (`.github/workflows/template-update.yml`) does
this every Monday and opens a pull request when there is a new template
release (run it by hand from the Actions tab). Conflicting changes are
committed with conflict markers in a draft pull request: resolve them on its
branch. There is one pull request per release, so closing one skips that
release. The template must be at a URL GitHub can clone (the `_src_path` in
`.copier-answers.yml`).

With the default `GITHUB_TOKEN`, enable "Allow GitHub Actions to create and
approve pull requests" (Settings → Actions → General). Even then the pull
request doesn't run CI, and updates that change `.github/workflows` can't be
pushed. To avoid both, add a `TEMPLATE_UPDATE_TOKEN` repository secret: a
fine-grained personal access token for this repository with read and write
access to Contents, Pull requests and Workflows.
