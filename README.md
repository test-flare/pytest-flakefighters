# Pytest FlakeFighters

[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![PyPI version](https://img.shields.io/pypi/v/pytest-flakefighters.svg)](https://pypi.org/project/pytest-flakefighters)
[![Python versions](https://img.shields.io/badge/python-3.10_--_3.14-blue)](https://pypi.org/project/pytest-flakefighters)
![Test status](https://github.com/test-flare/pytest-flakefighters/actions/workflows/ci-tests.yaml/badge.svg)
[![codecov](https://codecov.io/gh/test-flare/pytest-flakefighters/branch/main/graph/badge.svg?token=04ijFVrb4a)](https://codecov.io/gh/test-flare/pytest-flakefighters)
[![Documentation Status](https://readthedocs.org/projects/pytest-flakefighters/badge/?version=latest)](https://pytest-flakefighters.readthedocs.io/en/latest/?badge=latest)
![GitHub License](https://img.shields.io/github/license/test-flare/pytest-flakefighters)

### Pytest plugin implementing flaky test failure detection and classification.
Read more about flaky tests [here](https://docs.pytest.org/en/stable/explanation/flaky.html).

## Features

- Implements the [DeFlaker algorithm](http://www.deflaker.org/get-rid-of-your-flakes/) for pytest
- Implements two traceback-matching classifiers from [Alshammari et al. (2024)](https://doi.org/10.1109/ICST60714.2024.00031).
- Implements a novel coverage-independence classifier that classifies tests as flaky if they fail independently of passing test cases that exercise overlapping code.
- Optionally rerun or suppress flaky failures
- Output results to JSON, HTML, or JUnitXML
- Save test outcome history to a remote or local database

## Comparison with Other Plugins

Flakefighters is a pytest plugin developed as part of the [TestFLARE](https://test-flare.github.io/) project.
The plugin provides a "Swiss army knife" of techniques (called flakefighters) to detect flaky tests.
Where existing flaky test plugins such as [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) and [pytest-flaky](https://github.com/box/flaky) are primarily focused on rerunning (potentially) flaky tests until they pass, our main aim is to identify flaky tests by classifying test failures as genuine or flaky.
The [pytest-flakefinder](https://github.com/dropbox/pytest-flakefinder) plugin does this by simply rerunning tests multiple times and observing the result.

By contrast, Flakefighters incorporates several cutting edge flaky test detection techniques from research to automatically classify test failures as either genuine: indicating either a fault in the code or a mis-specified test case, or flaky: indicating a test with a nondeterministic outcome.
Flaky tests are then reported separately in the test report, and can be optionally rerun or suppressed so they don't block CI/CD pipelines.

| Feature | [pytest-flakefighters](https://github.com/test-flare/pytest-flakefighters) | [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) | [pytest-flaky](https://github.com/box/flaky) | [pytest-flakefinder](https://github.com/dropbox/pytest-flakefinder) | [pytest-replay](https://github.com/ESSS/pytest-replay) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Purpose** | Classify test failures as genuine or flaky | Rerun failing tests in case they are flaky | Decorator-based reruns | Copy tests to observe nondeterministic outcomes | Reproduce flaky failures from CI when running with [xdist](https://github.com/pytest-dev/pytest-xdist) |
| **Detection Method** | DeFlaker algorithm + coverage analysis | None | None | Reruns | None |
| **Reporting** | Terminal, HTML, JSON, JUnitXML | Terminal | Terminal | Terminal | Terminal |
| **History Tracking** | Database of test outcomes over commits | None | None | None | None |
| **Rerun Option** | Optional | Required | Required | Required | Required |
| **Suppression Option** | Optional | None | None | None | None |
| **Debugging support** | Insight into *why* tests are flaky | None | None | None | Reliable reproduction of flaky failures |

### When to Use pytest-flakefighters

Use pytest-flakefighters when you want to:

* **Understand WHY** tests are flaky, not just hide the symptoms
* **Classify** flaky tests by root cause (coverage-independent, traceback-matched, etc.)
* **Track** test flakiness over time and across commits
* **Make informed decisions** about whether failures are legitimate

### When to use alternatives

* [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures): Quick fix for CI builds
* [pytest-flaky](https://github.com/box/flaky): A few tests are known to be flaky
* [pytest-flakefinder](https://github.com/dropbox/pytest-flakefinder): Brute force search for flaky tests
* [pytest-replay](https://github.com/ESSS/pytest-replay): Debugging specific flaky failures

### Can They Work Together?

Yes! pytest-flakefighters can be combined with other flaky test plugins:

* Use **pytest-flakefighters** to identify and classify flaky tests
* Use [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) or [pytest-flaky](https://github.com/box/flaky) as a temporary measure while fixing them
* Use [pytest-replay](https://github.com/ESSS/pytest-replay) to debug specific instances identified by flakefighters
* Use [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) to randomise the order of your test cases

---

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

You can install \"pytest-flakefighters\" by cloning this repo and running `pip install .` from the root directory.
If you intend to develop the plugin, run `pip install -e .[dev]` instead.

If you use [uv](https://github.com/astral-sh/uv), you can install pytest-flakefighters with:

```bash
# Install with uv
uv pip install .

# For development
uv pip install -e .[dev]
```

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
By default, the plugin will only use the DeFlaker algorithm to classify flaky tests.
If you would like to use other algorithms as well (or instead), you need to configure these.
This can be done by adding appropriate fields in your pyproject.toml or pytest.ini file.
For example, you could add the following to your pyproject.toml.

```
[tool.pytest.ini_options.pytest_flakefighters.flakefighters.deflaker.DeFlaker]
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
