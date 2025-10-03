# pytest-flakefighter

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
If you need to call `pytest` from outside your repo, you can pass in the path to your repo as an additional parameter, `pytest --repo=path/to-repo`.

By default, flakefighter will compare the most recent commit (or local uncommitted changes if there are any) to the previous commit.
To compare an aribtrary pair of commits, you can call `pytest --source-commit=<commit_hash> --target-commit=<commit_hash>`, where `--source-commit` represents the older commit and `--target-commit` represents the newer commit.

## Contributing

Contributions are very welcome.
Tests can be run with [pytest](https://pytest.readthedocs.io/en/latest/), please ensure the coverage at least stays the same before you submit a pull request.

## Issues

If you encounter any problems, please [file an issue](https://github.com/test-flare/pytest-flakefighter/issues) along with a detailed description.
