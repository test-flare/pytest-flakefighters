"""
This module adds all the FlakeFighter configuration options to pytest.
"""

import logging
from importlib.metadata import entry_points

import coverage
import pytest
import yaml

from pytest_flakefighters.config import options
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
    # Allows users to specify flakefighter configurations in their pyproject.toml file without pytest throwing out
    # "unknown configuration option" warnings
    parser.addini("pytest_flakefighters", type="args", help="Configuration for the pytest-flakefighters extension")

    def datatype(details):
        if "type" not in details:
            return None
        if details["type"] is str:
            return "string"
        return str(details["type"].__name__)

    group = parser.getgroup("flakefighters")
    for name, details in options.items():
        # Add a commandline option with short name if provided, e.g. "--custom-option"
        # We need the default to be None here so that we can test if the user has provided it
        group.addoption(*name, **(details | {"default": None}))
        # Add configuration file option with no "--" and "-" replaced by "_"
        parser.addini(
            name[0][2:].replace("-", "_"),
            help=details["help"],
            default=details.get("default"),
            type=datatype(details),
        )


def get_config_value(config, name):
    """
    Get the configuration value.
    Options specified on the commandline will override those specified in configuration files.
    If neither is specified, the default value specified in `options.py` will be used.
    """
    cli_val = config.getoption(name)
    if cli_val is not None:
        return cli_val

    try:
        return config.getini(name)
    except ValueError:
        return None


def pytest_configure(config: pytest.Config):
    """
    Initialise the FlakeFighterPlugin class.
    :param config: The config options.
    """
    # Skip plugin registration if disabled
    if get_config_value(config, "no_flakefighters"):
        return
    
    database = Database(
        get_config_value(config, "database_url"),
        get_config_value(config, "load_max_runs"),
        get_config_value(config, "store_max_runs"),
        get_config_value(config, "time_immemorial"),
    )

    if get_config_value(config, "function_coverage"):
        cov = Profiler()
    else:
        cov = coverage.Coverage()

    algorithms = {ff.name: ff for ff in entry_points(group="pytest_flakefighters")}
    flakefighter_configs = config.inicfg.get("pytest_flakefighters")

    flakefighters = []
    if flakefighter_configs is not None:
        # Can't measure coverage since the branch taken depends on the python version
        if isinstance(flakefighter_configs, str):  # pragma: no cover
            flakefighter_configs = yaml.safe_load(flakefighter_configs)  # pragma: no cover
        elif hasattr(flakefighter_configs, "value"):  # pragma: no cover
            flakefighter_configs = yaml.safe_load(flakefighter_configs.value)  # pragma: no cover
        else:  # pragma: no cover
            raise TypeError(f"Unexpected type for config: {type(flakefighter_configs)}")  # pragma: no cover
        for module, classes in flakefighter_configs["flakefighters"].items():
            for class_name, params in classes.items():
                if class_name in algorithms:
                    flakefighters.append(
                        algorithms[class_name]
                        .load()
                        .from_config(
                            {k: get_config_value(config, k) for k in vars(config.option)}
                            | {"database": database}
                            | params
                        )
                    )
                else:
                    raise ValueError(
                        f"Could not load flakefighter {module}:{class_name}. Did you register its entry point?"
                    )

    else:
        logger.warning("No flakefighters specified. Using basic DeFlaker only.")
        flakefighters.append(
            DeFlaker(
                run_live=True,
                root=get_config_value(config, "root"),
            )
        )

    config.pluginmanager.register(
        FlakeFighterPlugin(
            root=get_config_value(config, "root"),
            database=database,
            cov=cov,
            flakefighters=flakefighters,
            rerun_strategy=rerun_strategy(
                get_config_value(config, "rerun_strategy"), get_config_value(config, "max_reruns"), database=database
            ),
            save_run=not get_config_value(config, "no_save"),
            display_outcomes=get_config_value(config, "display_outcomes"),
            display_verdicts=get_config_value(config, "display_verdicts"),
        )
    )
