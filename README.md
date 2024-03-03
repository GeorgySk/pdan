pdan
===========


[![](https://travis-ci.org/LostFan123/pdan.svg?branch=master)](https://travis-ci.org/LostFan123/pdan "Travis CI")
[![](https://dev.azure.com/skorobogatov/pdan/_apis/build/status/LostFan123.pdan?branchName=master)](https://dev.azure.com/skorobogatov/pdan/_build/latest?definitionId=2&branchName=master "Azure Pipelines")
[![](https://codecov.io/gh/LostFan123/pdan/branch/master/graph/badge.svg)](https://codecov.io/gh/LostFan123/pdan "Codecov")
[![](https://img.shields.io/github/license/LostFan123/pdan.svg)](https://github.com/LostFan123/pdan/blob/master/LICENSE "License")
[![](https://badge.fury.io/py/pdan.svg)](https://badge.fury.io/py/pdan "PyPI")

Summary
-------

`pdan` is a Python library that implements the algorithm of 
[Skorobogatov, G. et al., 2021](https://ieeexplore.ieee.org/abstract/document/9646907)
for convex polygon decomposition into separate parts depending on the area 
requirements.

---

In what follows
- `python` is an alias for `python3.8` or any later
version (`python3.9` and so on).

Installation
------------

Install the latest `pip` & `setuptools` packages versions:
  ```bash
  python -m pip install --upgrade pip setuptools
  ```

### User

Download and install the latest stable version from `PyPI` repository:
  ```bash
  python -m pip install --upgrade pdan
  ```

### Developer

Download the latest version from `GitHub` repository
```bash
git clone https://github.com/LostFan123/pdan.git
cd pdan
```

Install dependencies:
  ```bash
  poetry install
  ```

Usage
-----------
```python
>>> from pdan import minimizing_split, Contour, Point, Polygon
>>> contour = Contour([Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)])
>>> part, other = minimizing_split(contour, 0.5, key=lambda x, y: x.length)
>>> Polygon(part).area == Polygon(other).area == 0.5
True

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

### Running tests

Plain:
  ```bash
  pytest
  ```

Inside `Docker` container:
  ```bash
  docker compose up
  ```

`Bash` script (e.g. can be used in `Git` hooks):
  ```bash
  ./run-tests.sh
  ```
  or
  ```bash
  ./run-tests.sh cpython
  ```

`PowerShell` script (e.g. can be used in `Git` hooks):
  ```powershell
  .\run-tests.ps1
  ```
  or
  ```powershell
  .\run-tests.ps1 cpython
  ```
