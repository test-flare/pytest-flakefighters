"""
This module adds all the FlakeFighter configuration options to pytest.
"""

import logging
from importlib.metadata import entry_points, version
from typing import Any

import coverage
import pytest
import yaml
from packaging.version import Version

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
        # Support for ini int was only added in pytest>=3.9, but it seems to handle them fine as strings
        if details["type"] is str or (Version(version("pytest")) <= Version("9.0.0") and details["type"] is int):
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


def setup_flakefighter_configs(flakefighter_configs: Any):
    """
    Parse the flakefighter configurations from string, or initialise to empty if None.
    :param flakefighter_configs: The flakefighter config object.
    """
    # Can't measure coverage since the branch taken depends on the python version
    if isinstance(flakefighter_configs, str):  # pragma: no cover
        return yaml.safe_load(flakefighter_configs)["flakefighters"]  # pragma: no cover
    if hasattr(flakefighter_configs, "value"):  # pragma: no cover
        return yaml.safe_load(flakefighter_configs.value)["flakefighters"]  # pragma: no cover
    if flakefighter_configs is None:
        return {}
    raise TypeError(f"Unexpected type for config: {type(flakefighter_configs)}")  # pragma: no cover


def pytest_configure(config: pytest.Config):
    """
    Initialise the FlakeFighterPlugin class.
    :param config: The config options.
    """
    # Skip plugin registration if disabled
    if not get_config_value(config, "flakefighters"):
        return

    if get_config_value(config, "root") is None:
        config.option.root = str(config.rootdir)

    max_runs = get_config_value(config, "load_max_runs")
    database = Database(
        get_config_value(config, "database_url"),
        max_runs if max_runs != "" else None,
        get_config_value(config, "store_max_runs"),
        get_config_value(config, "time_immemorial"),
    )

    cov = Profiler() if get_config_value(config, "function_coverage") else coverage.Coverage()

    algorithms = {ff.name: ff for ff in entry_points(group="pytest_flakefighters")}
    flakefighter_configs = config.inicfg.get("pytest_flakefighters")

    active_flakefighters = get_config_value(config, "active_flakefighters")

    flakefighters = []
    if flakefighter_configs is None and active_flakefighters is None:
        logger.warning("No flakefighters specified. Using basic DeFlaker only.")
        flakefighters.append(
            DeFlaker(
                run_live=True,
                root=get_config_value(config, "root"),
            )
        )
    else:
        flakefighter_configs = setup_flakefighter_configs(flakefighter_configs)
        if active_flakefighters is not None:
            flakefighter_configs = {
                module: {
                    # Commandline --active-flakefighers overrides file options
                    class_name: config | {"active": class_name in active_flakefighters}
                    for class_name, config in configs.items()
                    if class_name in active_flakefighters
                }
                for module, configs in flakefighter_configs.items()
            }
            for class_name in active_flakefighters:
                module = algorithms[class_name].value.split(":")[0].split(".")[-1]
                flakefighter_configs[module] = flakefighter_configs.get(module, {})
                flakefighter_configs[module][class_name] = flakefighter_configs[module].get(class_name, {})

        for module, classes in flakefighter_configs.items():
            for class_name, params in classes.items():
                if class_name not in algorithms:
                    raise ValueError(
                        f"Could not load flakefighter {module}:{class_name}. Did you register its entry point?"
                    )
                if params.get("active", True):
                    flakefighters.append(
                        algorithms[class_name]
                        .load()
                        .from_config(
                            {k: get_config_value(config, k) for k in vars(config.option)}
                            | {"database": database}
                            | params
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
        ),
        name="flakefighter_plugin",
    )
