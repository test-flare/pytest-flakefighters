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

You can install \"pytest-flakefighter\" via [pip](https://pypi.org/project/pip/) from [PyPI](https://pypi.org/project):
```
pip install pytest-flakefighter
```

## Usage

FlakeFighter is intended to run on git repositories that have test suites runnable with `pytest`.
Once you have installed FlakeFighter, you can run it from the root directory of your repo simply by running `pytest` in your usual way.
If you need to call `pytest` from outside your repo, you can pass in the path to your repo as an additional parameter, `pytest --repo=path/to-repo`.

By default, the DeFlaker algorithm will compare the most recent commit to the previous commit.
This is to allow it to work with Continuous Integration actions.
However, if you would like to run it with a historical commit, you can include this as an extra argument `pytest --commit=<commit_hash>`.
We do not currently support comparison with uncommitted code.

## Contributing

Contributions are very welcome.
Tests can be run with [pytest](https://pytest.readthedocs.io/en/latest/), please ensure the coverage at least stays the same before you submit a pull request.

## Issues

If you encounter any problems, please [file an issue](https://github.com/test-flare/pytest-flakefighter/issues) along with a detailed description.
