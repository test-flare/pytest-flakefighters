# Pytest FlakeFighters

[![PyPI version](https://img.shields.io/pypi/v/pytest-flakefighter.svg)](https://pypi.org/project/pytest-flakefighter)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-flakefighter.svg)](https://pypi.org/project/pytest-flakefighter)

Pytest plugin implementing flaky test failure detection and
classification.

------------------------------------------------------------------------

This [pytest](https://github.com/pytest-dev/pytest) plugin was generated with [Cookiecutter](https://github.com/audreyr/cookiecutter) along with [\@hackebrot](https://github.com/hackebrot)\'s [cookiecutter-pytest-plugin](https://github.com/pytest-dev/cookiecutter-pytest-plugin) template.

## Features

-   Implements the [DeFlaker algorithm](https://deflaker.com/) for pytest


## Installation

You can install \"pytest-flakefighter\" by cloning this repo and running `pip install .` from the root directory.
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
  --no-save             Do not save this run to the database of previous flakefighter runs.
  -M LOAD_MAX_RUNS, --load-max-runs=LOAD_MAX_RUNS
                        The maximum number of previous runs to consider.
  -D DATABASE_URL, --database-url=DATABASE_URL
                        The database URL. Defaults to 'flakefighter.db' in current working directory.
  --store-max-runs=STORE_MAX_RUNS
                        The maximum number of previous flakefighter runs to store. Default is to store all.
  --time-immemorial=TIME_IMMEMORIAL
                        How long to store flakefighter runs for, specified as `days:hours:minutes`. E.g. to store
                        tests for one week, use 7:0:0.
```

## Contributing

Contributions are very welcome.
Tests can be run with [pytest](https://pytest.readthedocs.io/en/latest/), please ensure the coverage at least stays the same before you submit a pull request.

## Issues

If you encounter any problems, please [file an issue](https://github.com/test-flare/pytest-flakefighter/issues) along with a detailed description.
