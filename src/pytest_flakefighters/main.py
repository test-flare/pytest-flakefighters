"""
This module adds all the FlakeFighter configuration options to pytest.
"""

import logging
import os
from importlib.metadata import entry_points

import coverage
import pytest
import yaml

from pytest_flakefighters.database_management import Database
from pytest_flakefighters.flakefighters.deflaker import DeFlaker
from pytest_flakefighters.function_coverage import Profiler
from pytest_flakefighters.plugin import FlakeFighterPlugin
from pytest_flakefighters.rerun_strategies import All, FlakyFailure, PreviouslyFlaky

rerun_strategies = {"ALL": All, "FLAKY_FAILURE": FlakyFailure, "PREVIOUSLY_FLAKY": PreviouslyFlaky}

logger = logging.getLogger(__name__)


def rerun_strategy(strategy: str, max_reruns: int, **kwargs):
    """
    Instantiate the selected rerun strategy.
    """
    if strategy == "PREVIOUSLY_FLAKY":
        return PreviouslyFlaky(max_reruns, kwargs["database"])
    return rerun_strategies[strategy](max_reruns)


def pytest_addoption(parser: pytest.Parser):
    """
    Add extra pytest options.
    :param parser: The argument parser.
    """
    group = parser.getgroup("flakefighters")
    group.addoption(
        "--root",
        dest="root",
        action="store",
        default=os.getcwd(),
        help="The root directory of the project. Defaults to the current working directory.",
    )
    group.addoption(
        "--suppress-flaky-failures-exit-code",
        dest="suppress_flaky",
        action="store_true",
        default=False,
        help="Return OK exit code if the only failures are flaky failures.",
    )
    group.addoption(
        "--no-save",
        action="store_true",
        default=False,
        help="Do not save this run to the database of previous flakefighters runs.",
    )
    group.addoption(
        "--function-coverage",
        action="store_true",
        default=False,
        help="Use function-level coverage instead of line coverage.",
    )
    group.addoption(
        "--load-max-runs",
        "-M",
        action="store",
        default=None,
        help="The maximum number of previous runs to consider.",
    )
    group.addoption(
        "--database-url",
        "-D",
        action="store",
        default="sqlite:///flakefighters.db",
        help="The database URL. Defaults to 'flakefighters.db' in current working directory.",
    )
    group.addoption(
        "--store-max-runs",
        action="store",
        default=None,
        type=int,
        help="The maximum number of previous flakefighters runs to store. Default is to store all.",
    )
    group.addoption(
        "--max-reruns",
        action="store",
        default=0,
        type=int,
        help="The maximum number of times to rerun tests. "
        "By default, only failing tests marked as flaky will be rerun. "
        "This can be changed with the --rerun-strategy parameter.",
    )
    group.addoption(
        "--rerun-strategy",
        action="store",
        type=str,
        choices=list(rerun_strategies),
        default="FLAKY_FAILURE",
        help="The strategy used to determine which tests to rerun. Supported options are:\n  "
        + "\n  ".join(f"{name} - {strat.help()}" for name, strat in rerun_strategies.items()),
    )
    group.addoption(
        "--time-immemorial",
        action="store",
        default=None,
        help="How long to store flakefighters runs for, specified as `days:hours:minutes`. "
        "E.g. to store tests for one week, use 7:0:0.",
    )


def pytest_configure(config: pytest.Config):
    """
    Initialise the FlakeFighterPlugin class.
    :param config: The config options.
    """
    database = Database(
        config.option.database_url,
        config.option.load_max_runs,
        config.option.store_max_runs,
        config.option.time_immemorial,
    )

    if config.option.function_coverage:
        cov = Profiler()
    else:
        cov = coverage.Coverage()

    algorithms = entry_points(group="pytest_flakefighters")
    flakefighter_configs = config.inicfg.get("pytest_flakefighters")

    flakefighters = []
    if flakefighter_configs:
        flakefighter_configs = yaml.safe_load(flakefighter_configs.value)
        for flakefighter in algorithms:
            if flakefighter.name in flakefighter_configs:
                flakefighters.append(
                    flakefighter.load().from_config(
                        vars(config.option) | {"database": database} | flakefighter_configs[flakefighter.name]
                    )
                )

    else:
        logger.warning("No flakefighters specified. Using basic DeFlaker only.")
        flakefighters.append(
            DeFlaker(
                run_live=True,
                root=config.option.root,
            )
        )

    config.pluginmanager.register(
        FlakeFighterPlugin(
            root=config.option.root,
            database=database,
            cov=cov,
            flakefighters=flakefighters,
            rerun_strategy=rerun_strategy(config.option.rerun_strategy, config.option.max_reruns, database=database),
            save_run=not config.option.no_save,
        )
    )
