# Pytest FlakeFighters
### Pytest plugin implementing flaky test failure detection and classification.

[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![PyPI version](https://img.shields.io/pypi/v/pytest-flakefighters.svg)](https://pypi.org/project/pytest-flakefighters)
[![Python versions](https://img.shields.io/badge/python-3.10_--_3.13-blue)](https://pypi.org/project/pytest-flakefighters)
![Test status](https://github.com/test-flare/pytest-flakefighters/actions/workflows/ci-tests.yaml/badge.svg)
[![codecov](https://codecov.io/gh/test-flare/pytest-flakefighters/branch/main/graph/badge.svg?token=04ijFVrb4a)](https://codecov.io/gh/test-flare/pytest-flakefighters)
[![Documentation Status](https://readthedocs.org/projects/causal-testing-framework/badge/?version=latest)](https://causal-testing-framework.readthedocs.io/en/latest/?badge=latest)
![GitHub License](https://img.shields.io/github/license/test-flare/pytest-flakefighters)



## Features

-   Implements the [DeFlaker algorithm](https://deflaker.com/) for pytest


## Installation

You can install \"pytest-flakefighters\" by cloning this repo and running `pip install .` from the root directory.
If you intend to develop the plugin, run `pip install -e .[dev]` instead.

We eventually intend to distribute our tool on PyPI.

## Usage

FlakeFighter is intended to run on git repositories that have test suites runnable with `pytest`.
Once you have installed FlakeFighter, you can run it from the root directory of your repo simply by running `pytest` in your usual way.
FlakeFighter has the following arguments.

```
  --target-commit=TARGET_COMMIT
                        The target (newer) commit hash. Defaults to HEAD (the most recent commit).
  --source-commit=SOURCE_COMMIT
                        The source (older) commit hash. Defaults to HEAD^ (the previous commit to target).
  --repo=REPO_ROOT      The commit hash to compare against.
  --suppress-flaky-failures-exit-code
                        Return OK exit code if the only failures are flaky failures.
  --no-save             Do not save this run to the database of previous flakefighters runs.
  -M LOAD_MAX_RUNS, --load-max-runs=LOAD_MAX_RUNS
                        The maximum number of previous runs to consider.
  -D DATABASE_URL, --database-url=DATABASE_URL
                        The database URL. Defaults to 'flakefighter.db' in current working directory.
  --store-max-runs=STORE_MAX_RUNS
                        The maximum number of previous flakefighters runs to store. Default is to store all.
  --time-immemorial=TIME_IMMEMORIAL
                        How long to store flakefighters runs for, specified as `days:hours:minutes`. E.g. to store
                        tests for one week, use 7:0:0.
```

## Contributing

Contributions are very welcome.
Tests can be run with [pytest](https://pytest.readthedocs.io/en/latest/), please ensure the coverage at least stays the same before you submit a pull request.

## Flake Fighters
Our plugin is made up of a collection of heuristics that come together to help inform whether a test failure is genuine or flaky.
These come in two "flavours": those which run live after each test, and those which run at the end of the entire test suite.
Both extend the base class `FlakeFighter` and implement the `flaky_failure` method, which returns `True` if the test is deemed to be flaky.

## Issues

If you encounter any problems, please [file an issue](https://github.com/test-flare/pytest-flakefighters/issues) along with a detailed description.

------------------------------------------------------------------------

This [pytest](https://github.com/pytest-dev/pytest) plugin was generated with [Cookiecutter](https://github.com/audreyr/cookiecutter) along with [\@hackebrot](https://github.com/hackebrot)\'s [cookiecutter-pytest-plugin](https://github.com/pytest-dev/cookiecutter-pytest-plugin) template.
