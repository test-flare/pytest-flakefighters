"""
This module adds all the FlakeFighter configuration options to pytest.
"""

import coverage
import pytest

from pytest_flakefighters.database_management import Database
from pytest_flakefighters.flakefighters.coverage_independence import (
    CoverageIndependence,
)
from pytest_flakefighters.flakefighters.deflaker import DeFlaker
from pytest_flakefighters.function_coverage import Profiler
from pytest_flakefighters.plugin import FlakeFighterPlugin


def pytest_addoption(parser: pytest.Parser):
    """
    Add extra pytest options.
    :param parser: The argument parser.
    """
    group = parser.getgroup("flakefighter")
    group.addoption(
        "--target-commit",
        action="store",
        dest="target_commit",
        default=None,
        help="The target (newer) commit hash. Defaults to HEAD (the most recent commit).",
    )
    group.addoption(
        "--source-commit",
        action="store",
        dest="source_commit",
        default=None,
        help="The source (older) commit hash. Defaults to HEAD^ (the previous commit to target).",
    )
    group.addoption(
        "--repo",
        action="store",
        dest="repo_root",
        default=None,
        help="The root directory of the Git repository. Defaults to the current working directory.",
    )
    group.addoption(
        "--suppress-flaky-failures-exit-code",
        action="store_true",
        dest="suppress_flaky",
        default=False,
        help="Return OK exit code if the only failures are flaky failures.",
    )
    group.addoption(
        "--no-save",
        action="store_true",
        dest="no_save",
        default=False,
        help="Do not save this run to the database of previous flakefighters runs.",
    )
    group.addoption(
        "--function-coverage",
        action="store_true",
        dest="function_coverage",
        default=False,
        help="Use function-level coverage instead of line coverage.",
    )
    group.addoption(
        "--load-max-runs",
        "-M",
        action="store",
        dest="load_max_runs",
        default=None,
        help="The maximum number of previous runs to consider.",
    )
    group.addoption(
        "--database-url",
        "-D",
        action="store",
        dest="database_url",
        default="sqlite:///flakefighters.db",
        help="The database URL. Defaults to 'flakefighters.db' in current working directory.",
    )
    group.addoption(
        "--store-max-runs",
        action="store",
        dest="store_max_runs",
        default=None,
        type=int,
        help="The maximum number of previous flakefighters runs to store. Default is to store all.",
    )
    group.addoption(
        "--max-flaky-reruns",
        action="store",
        dest="max_flaky_reruns",
        default=0,
        type=int,
        help="The maximum number of times to rerun tests classified as flaky. Default is not to rerun.",
    )
    group.addoption(
        "--time-immemorial",
        action="store",
        dest="time_immemorial",
        default=None,
        help="How long to store flakefighters runs for, specified as `days:hours:minutes`. "
        "E.g. to store tests for one week, use 7:0:0.",
    )
    group.addoption(
        "--coverage-distaince-threshold",
        action="store",
        dest="coverage_distaince_threshold",
        default=0,
        help="The minimum distance to consider as 'similar', expressed as a proportion 0 <= threshold < 1 where 0 "
        "represents no difference and 1 represents complete difference.",
    )
    group.addoption(
        "--coverage-distaince-metric",
        action="store",
        dest="coverage_distaince_metric",
        default="jaccard",
        help="The metric to use when computing the distance between coverage.",
    )


def pytest_configure(config: pytest.Config):
    """
    Initialise the FlakeFighterPlugin class.
    :param config: The config options.
    """
    repo_root = config.option.repo_root
    target_commit = config.option.target_commit
    source_commit = config.option.source_commit

    if config.option.function_coverage:
        cov = Profiler()
    else:
        cov = coverage.Coverage()

    config.pluginmanager.register(
        FlakeFighterPlugin(
            database=Database(config.option.database_url, config.option.store_max_runs, config.option.time_immemorial),
            cov=cov,
            flakefighters=[
                DeFlaker(run_live=True, repo_root=repo_root, source_commit=source_commit, target_commit=target_commit),
                CoverageIndependence(
                    threshold=config.option.coverage_distaince_threshold, metric=config.option.coverage_distaince_metric
                ),
            ],
            target_commit=target_commit,
            source_commit=source_commit,
            load_max_runs=config.option.load_max_runs,
            max_flaky_reruns=config.option.max_flaky_reruns,
            save_run=not config.option.no_save,
        )
    )
