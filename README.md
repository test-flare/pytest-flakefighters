# Pytest FlakeFighters

[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![PyPI version](https://img.shields.io/pypi/v/pytest-flakefighters.svg)](https://pypi.org/project/pytest-flakefighters)
[![Python versions](https://img.shields.io/badge/python-3.10_--_3.14-blue)](https://pypi.org/project/pytest-flakefighters)
![Test status](https://github.com/test-flare/pytest-flakefighters/actions/workflows/ci-tests.yaml/badge.svg)
[![codecov](https://codecov.io/gh/test-flare/pytest-flakefighters/branch/main/graph/badge.svg?token=04ijFVrb4a)](https://codecov.io/gh/test-flare/pytest-flakefighters)
[![Documentation Status](https://readthedocs.org/projects/pytest-flakefighters/badge/?version=latest)](https://pytest-flakefighters.readthedocs.io/en/latest/?badge=latest)
![GitHub License](https://img.shields.io/github/license/test-flare/pytest-flakefighters)

## Quick Start

- What is `pytest-flakefighters`? It is a pytest plugin for flaky test failure
  detection and classification.
- Want to learn more? Read more about flaky tests [in pytest's official
  description](https://docs.pytest.org/en/stable/explanation/flaky.html).
- Ready to get started? Follow this quick start guide!

```bash
# Install the plugin as a dev dependency
uv add --dev pytest-flakefighters

# Run your tests with flakefighters enabled
uv run pytest --flakefighters
```

For more details, see the [Installation](#installation) and [Usage](#usage) sections below.

## Features of Pytest FlakeFighters

- Implements differential coverage, inspired by the [DeFlaker algorithm](http://www.deflaker.org/get-rid-of-your-flakes/), for pytest
- Implements two traceback-matching classifiers from [Alshammari et al. (2024)](https://doi.org/10.1109/ICST60714.2024.00031)
- Implements a novel coverage-independence classifier that classifies tests as flaky if they fail independently of passing test cases that exercise overlapping code
- Optionally reruns or suppress flaky test failures
- Outputs its results to JSON, HTML, or JUnitXML
- Saves test outcome history to a remote or local database

## Comparison with Other Plugins

Flakefighters is a pytest plugin developed as part of the [TestFLARE](https://test-flare.github.io/) project.
The plugin provides a "Swiss army knife" of techniques, called flakefighters, to detect flaky tests.
Where existing flaky test plugins such as [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) and [pytest-flaky](https://github.com/box/flaky) are primarily focused on rerunning (potentially) flaky tests until they pass, our main aim is to identify flaky tests by classifying test failures as _genuine_ or _flaky_.
The [pytest-flakefinder](https://github.com/dropbox/pytest-flakefinder) plugin does this by simply rerunning tests multiple times and observing the result.

In contrast, Flakefighters incorporates several cutting-edge flaky test detection techniques from research to automatically classify test failures as either _genuine_: indicating either a fault in the code or a mis-specified test case, or _flaky_: indicating a test with a nondeterministic outcome.
Flaky tests are then reported separately in the test report, and can be optionally rerun or suppressed so they don't block CI/CD pipelines.

| Feature | [pytest-flakefighters](https://github.com/test-flare/pytest-flakefighters) | [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) | [pytest-flaky](https://github.com/box/flaky) | [pytest-flakefinder](https://github.com/dropbox/pytest-flakefinder) | [pytest-replay](https://github.com/ESSS/pytest-replay) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Purpose** | Classify test failures as genuine or flaky | Rerun failing tests in case they are flaky | Decorator-based reruns | Copy tests to observe nondeterministic outcomes | Reproduce flaky failures from CI when running with [xdist](https://github.com/pytest-dev/pytest-xdist) |
| **Detection Method** | Differential coverage | None | None | Reruns | None |
| **Reporting** | Terminal, HTML, JSON, JUnitXML | Terminal | Terminal | Terminal | Terminal |
| **History Tracking** | Database of test outcomes over commits | None | None | None | None |
| **Rerun Option** | Optional | Required | Required | Required | Required |
| **Suppression Option** | Optional | None | None | None | None |
| **Debugging support** | Insight into *why* tests are flaky | None | None | None | Reliable reproduction of flaky failures |

### When to Use pytest-flakefighters

Use `pytest-flakefighters` when you want to:

- **Understand** why tests are flaky, not just hide the symptoms
- **Classify** flaky tests by root cause (e.g., coverage-independent or traceback-matched)
- **Track** test flakiness over time and across commits
- **Make informed decisions** about whether failures are legitimate

### When to Use Alternatives

- [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures): Quick fix for CI builds
- [pytest-flaky](https://github.com/box/flaky): A few tests are known to be flaky
- [pytest-flakefinder](https://github.com/dropbox/pytest-flakefinder): Brute force search for flaky tests
- [pytest-replay](https://github.com/ESSS/pytest-replay): Debugging specific flaky failures

### Can They Work Together?

Yes! The pytest-flakefighters plugin can be combined with other flaky test plugins:

- Use **pytest-flakefighters** to identify and classify flaky tests
- Use [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) or [pytest-flaky](https://github.com/box/flaky) as a temporary measure while fixing them
- Use [pytest-replay](https://github.com/ESSS/pytest-replay) to debug specific instances identified by flakefighters
- Use [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) to randomise the order of your test cases

______________________________________________________________________

*For more information on flaky test management best practices, see the [pytest documentation](https://docs.pytest.org/en/stable/explanation/flaky.html).*

## Installation

### With pip

You can install the extension by running `pip install pytest-flakefighters` from within your project's virtual environment.

### With uv

If you use [uv](https://github.com/astral-sh/uv) for Python package management, you can install pytest-flakefighters with `uv add pytest-flakefighters`.
This will add the plugin to your main dependencies.

```
dependencies = [
    "pytest-flakefighters>=x.y.z",
]
```

However, pytest is typically a [development dependency](https://docs.astral.sh/uv/concepts/projects/dependencies/#development-dependencies), and so should be added with `uv add --dev pytest-flakefighters`.

```
[dependency-groups]
dev = [
    "pytest-flakefighters>=x.y.z",
]
```

### From source (for development)

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and running tasks.
After cloning the repository, create the virtual environment and install all dependencies (including development tools) with:

```bash
# Sync the lockfile and install the project in editable mode with dev dependencies
uv sync --extra dev
```

This is the recommended workflow because it uses the project's `uv.lock` file and guarantees a reproducible environment.

If you prefer the lower-level pip-compatible interface, you can still run:

```bash
# Editable install with development dependencies
uv pip install -e .[dev]
```

> [!NOTE]
> `uv pip install -e .[dev]` does not update `uv.lock`. Use `uv sync --extra dev` when you want the lockfile to stay in sync.

## Usage

FlakeFighter is intended to run on Git repositories that have test suites runnable with `pytest`.
Once you have installed FlakeFighter, you can run it from the root directory of your repo simply by running `pytest` (or `uv run pytest` if you are using uv without activating the virtual environment).
FlakeFighter has the following arguments.

```
  --flakefighters       Enable the flakefighters plugin.
  --root=ROOT           The root directory of the project. Defaults to the current working directory.
  --suppress-flaky-failures-exit-code
                        Return OK exit code if the only failures are flaky failures.
  --no-save             Do not save this run to the database of previous flakefighters runs.
  --function-coverage   Use function-level coverage instead of line coverage.
  -M LOAD_MAX_RUNS, --load-max-runs=LOAD_MAX_RUNS
                        The maximum number of previous runs to consider.
  -D DATABASE_URL, --database-url=DATABASE_URL
                        The database URL. Defaults to 'flakefighters.db' in current working directory.
  --store-max-runs=STORE_MAX_RUNS
                        The maximum number of previous flakefighters runs to store. Default is to store all.
  --max-reruns=MAX_RERUNS
                        The maximum number of times to rerun tests. By default, only failing tests marked as flaky
                        will be rerun. This can be changed with the --rerun-strategy parameter.
  --rerun-strategy={ALL,FLAKY_FAILURE,PREVIOUSLY_FLAKY}
                        The strategy used to determine which tests to rerun. Supported options are:
                        ALL - Trivially rerun all tests, regardless of outcome.
                        FLAKY_FAILURE - Rerun failing tests that have been merked as flaky by live FlakeFighters.
                        PREVIOUSLY_FLAKY - Rerun failing tests marked as flaky, and tests that have previously been
                        marked as flaky.
  --time-immemorial=TIME_IMMEMORIAL
                        How long to store flakefighters runs for, specified as `days:hours:minutes`. E.g. to store
                        tests for one week, use 7:0:0.
  -O [DISPLAY_OUTCOMES], --display-outcomes=[DISPLAY_OUTCOMES]
                        Display historical test outcomes of the specified number of previous runs.If no value is
                        specified, then display only the current verdict.
  --display-verdicts    Display the flaky classification verdicts alongside test outcomes.
  -A ACTIVE_FLAKEFIGHTERS [ACTIVE_FLAKEFIGHTERS ...], --active-flakefighters=ACTIVE_FLAKEFIGHTERS [ACTIVE_FLAKEFIGHTERS ...]
                        The names of the active flakefighters. If unspecified flakefighters with a specified
                        configuration will be used.Flakefighters can also be turned on and off individually with the
                        `active` configuration parameter
```

### Enabling/Disabling the Plugin

To enable the plugin, run pytest with the `--flakefighters` argument

```bash
pytest --flakefighters
```

You can also configure this in your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--flakefighters"
```

### Configuration

By default, the plugin will only use differential coverage to classify flaky tests.
If you would like to use other algorithms as well (or instead), you need to configure these.
This can be done by adding appropriate fields in your pyproject.toml or pytest.ini file.
For example, you could add the following to your pyproject.toml.

```
[tool.pytest.ini_options.pytest_flakefighters.flakefighters.diff_cov.DiffCov]
run_live=true # run the classifier immediately after each test

[tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.TracebackMatching]
run_live=false # run the classifier at the end of the test suite

[tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.CosineSimilarity]
run_live=false # run the classifier at the end of the test suite
threshold=0.8 # Cosine similarity >= 0.8 is classed as a match

[tool.pytest.ini_options.pytest_flakefighters.flakefighters.coverage_independence.CoverageIndependence]
run_live=false # run the classifier at the end of the test suite
threshold=0.1 # Distance <= 0.1 is classed as "similar"
metric=hamming # Use Hamming distance
linkage_method=complete # Use complete linkage for clustering
```

> [!NOTE]
> The above configuration is just an example meant to demonstrate the various parameters that can be supplied, and is not a recommendation or "default".
> You should choose the parameter values that are appropriate for your project, especially threshold values for CosineSimilarity and CoverageIndependence.

Further details can be found in the [configuration documentation](https://pytest-flakefighters.readthedocs.io/en/latest/configuration.html).

## Contributing

Contributions are very welcome.
Tests can be run with `uv run pytest` (or `pytest` after activating the virtual environment). Please ensure the coverage at least stays the same before you submit a pull request.

## Flake Fighters

The `pytest-flakefighters` plugin is made up of a collection of heuristics that come together to help inform whether a test failure is genuine or flaky.
These come in two "flavours": those which run live after each test, and those which run at the end of the entire test suite.
Both extend the base class `FlakeFighter` and implement the `flaky_failure` method, which returns `True` if the test is deemed to be flaky.

## Issues

If you encounter any problems, please [file an issue](https://github.com/test-flare/pytest-flakefighters/issues) along with a detailed description.

______________________________________________________________________

This [pytest](https://github.com/pytest-dev/pytest) plugin was generated with [Cookiecutter](https://github.com/audreyr/cookiecutter) along with [@hackebrot](https://github.com/hackebrot)'s [cookiecutter-pytest-plugin](https://github.com/pytest-dev/cookiecutter-pytest-plugin) template.
