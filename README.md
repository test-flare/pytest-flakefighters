# Pytest FlakeFighters

[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![PyPI version](https://img.shields.io/pypi/v/pytest-flakefighters.svg)](https://pypi.org/project/pytest-flakefighters)
[![Python versions](https://img.shields.io/badge/python-3.10_--_3.13-blue)](https://pypi.org/project/pytest-flakefighters)
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
- Optionally rerun flaky failures
- Output results to JSON, HTML, or JUnitXML
- Save test outcome history to a remote or local database

## Comparison with Other Plugins

pytest-flakefighters takes a fundamentally different approach to flaky tests compared to other popular pytest plugins.

### How pytest-flakefighters Differs

| Feature | pytest-flakefighters | pytest-rerunfailures | pytest-flaky |
|---------|---------------------|---------------------|--------------|
| **Approach** | Intelligent classification using algorithms | Simple rerun mechanism | Decorator-based reruns |
| **Detection Method** | DeFlaker algorithm + coverage analysis | None (only reruns) | None (only reruns) |
| **Classification** | Yes - identifies *why* test is flaky | No | No |
| **History Tracking** | Database of test outcomes over commits | No | No |
| **Academic Basis** | Research-backed algorithms | N/A | N/A |
| **Git Integration** | Yes - compares commits | No | No |
| **Rerun Option** | Optional | Required | Required |

### Popular Alternatives

#### [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures)
- **Purpose:** Rerun failed tests to work around temporary failures
- **Usage:** `pytest --reruns 3 --reruns-delay 2`
- **Best for:** Quick CI fixes when you just need passing builds
- **Limitation:** Doesn't identify *why* tests are flaky

#### [pytest-flaky](https://github.com/box/flaky)
- **Purpose:** Mark specific tests as flaky and rerun them
- **Usage:** `@flaky(max_runs=3, min_passes=2)`
- **Best for:** Known flaky tests that you want to pass "most of the time"
- **Limitation:** Manual marking required, no automatic detection

#### [pytest-flakefinder](https://github.com/dropbox/pytest-flakefinder)
- **Purpose:** Identify flaky tests by running them multiple times
- **Best for:** Discovery phase - finding which tests are flaky
- **Limitation:** Doesn't classify or explain flakiness

#### [pytest-replay](https://github.com/ESSS/pytest-replay)
- **Purpose:** Reproduce flaky failures from CI in local environment
- **Best for:** Debugging specific flaky test instances
- **Limitation:** Requires failure already occurred

### When to Use pytest-flakefighters

Use pytest-flakefighters when you want to:
- **Understand WHY** tests are flaky, not just hide the symptoms
- **Classify** flaky tests by root cause (coverage-independent, traceback-matched, etc.)
- **Track** test flakiness over time and across commits
- **Make informed decisions** about whether failures are legitimate

### When to Use Alternatives

- **pytest-rerunfailures:** Quick fix for CI builds, don't care about root cause
- **pytest-flaky:** You've already identified flaky tests manually
- **pytest-flakefinder:** Just want to discover which tests are flaky
- **pytest-replay:** Debugging a specific flaky failure instance

### Can They Work Together?

Yes! pytest-flakefighters can be combined with other plugins:
- Use **pytest-flakefighters** to identify and classify flaky tests
- Use **pytest-rerunfailures** as a temporary measure while fixing them
- Use **pytest-replay** to debug specific instances identified by flakefighters

---

*For more information on flaky test management best practices, see the [pytest documentation](https://docs.pytest.org/en/stable/explanation/flaky.html).*


## Installation

You can install \"pytest-flakefighters\" by cloning this repo and running `pip install .` from the root directory.
If you intend to develop the plugin, run `pip install -e .[dev]` instead.

### Installation with uv

If you use [uv](https://github.com/astral-sh/uv) for Python package management, you can install pytest-flakefighters with:

```bash
# Clone the repository
git clone https://github.com/test-flare/pytest-flakefighters.git
cd pytest-flakefighters

# Install with uv
uv pip install .

# For development
uv pip install -e .[dev]
```

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

### Enabling/Disabling the Plugin

By default, pytest-flakefighters runs whenever it is installed. To disable it for a specific test run, use:

```bash
pytest --no-flakefighters
```

This is useful when you have the plugin installed but want to run quick tests without flaky test detection.

You can also configure this in your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--no-flakefighters"
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
