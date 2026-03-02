"""
This module contains tests for the configuration setup.
"""

import os

from pytest_flakefighters.flakefighters.traceback_matching import CosineSimilarity
from pytest_flakefighters.main import pytest_configure


def test_flakefighters(pytester, deflaker_repo):
    """
    Test that flakefighters is registered when the --flakefighters argument is passed.
    """
    reprec = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "--flakefighters",
        "-s",
    ).reprec
    assert any(
        call.plugin_name == "flakefighters" for call in reprec.getcalls("pytest_plugin_registered")
    ), "Flakefighters should be registered when --no-flakefighters is not passed"


def test_no_flakefighters(pytester, deflaker_repo):
    """
    Test that flakefighters is not registered when the --flakefighters argument is not passed.
    """
    reprec = pytester.runpytest(
        os.path.join(deflaker_repo.working_dir, "app.py"),
        "-s",
        "--flakefighters",
    ).reprec
    assert any(
        call.plugin_name == "flakefighters" for call in reprec.getcalls("pytest_plugin_registered")
    ), "Flakefighters should not be registered when --no-flakefighters is passed"


def test_active_flakefighters_cmd(pytester, flaky_reruns_repo):
    """
    Test that only the specified active flakefighters are activated.
    """
    config = pytester.parseconfig(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "--flakefighters",
        "--active-flakefighters",
        "CosineSimilarity",
    )
    pytest_configure(config)

    plugin = config.pluginmanager.get_plugin("flakefighter_plugin")

    assert [f.__class__ for f in plugin.flakefighters] == [CosineSimilarity]
    assert [f.params() for f in plugin.flakefighters] == [
        {"run_live": True, "root": flaky_reruns_repo.working_dir, "threshold": 1}
    ]


def test_active_flakefighters_ini(pytester, flaky_reruns_repo):
    """
    Test that flakefighters with a valid configuration are activated.
    """
    with open(os.path.join(flaky_reruns_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.CosineSimilarity]\n"
            "run_live=false"
        )
    config = pytester.parseconfig(os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"), "--flakefighters")
    pytest_configure(config)

    plugin = config.pluginmanager.get_plugin("flakefighter_plugin")

    assert [f.__class__ for f in plugin.flakefighters] == [CosineSimilarity]
    assert [f.params() for f in plugin.flakefighters] == [
        {"run_live": False, "root": flaky_reruns_repo.working_dir, "threshold": 1}
    ]


def test_active_flakefighters_ini_cmd(pytester, flaky_reruns_repo):
    """
    Test that commandline --active-flakefighters overrides config.
    """
    with open(os.path.join(flaky_reruns_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.TracebackMatching]\n"
            "run_live=false"
        )
    config = pytester.parseconfig(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "--flakefighters",
        "--active-flakefighters",
        "CosineSimilarity",
    )
    pytest_configure(config)

    plugin = config.pluginmanager.get_plugin("flakefighter_plugin")

    assert [f.__class__ for f in plugin.flakefighters] == [CosineSimilarity]
    assert [f.params() for f in plugin.flakefighters] == [
        {"run_live": True, "root": flaky_reruns_repo.working_dir, "threshold": 1}
    ]


def test_active_flakefighters_active(pytester, flaky_reruns_repo):
    """
    Test that commandline --active-flakefighters overrides config.
    """
    with open(os.path.join(flaky_reruns_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.TracebackMatching]\n"
            "run_live=false\n"
            "active=false\n"
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.CosineSimilarity]\n"
            "run_live=false"
        )
    config = pytester.parseconfig(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "--flakefighters",
    )
    pytest_configure(config)

    plugin = config.pluginmanager.get_plugin("flakefighter_plugin")

    assert [f.__class__ for f in plugin.flakefighters] == [CosineSimilarity]
    assert [f.params() for f in plugin.flakefighters] == [
        {"run_live": False, "root": flaky_reruns_repo.working_dir, "threshold": 1}
    ]


def test_active_flakefighters_active_cmd(pytester, flaky_reruns_repo):
    """
    Test that commandline --active-flakefighters overrides config.
    """
    with open(os.path.join(flaky_reruns_repo.working_dir, "pyproject.toml"), "w") as f:
        f.write(
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.TracebackMatching]\n"
            "run_live=false\n"
            "[tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.CosineSimilarity]\n"
            "run_live=false\n"
            "active=false\n"
        )
    config = pytester.parseconfig(
        os.path.join(flaky_reruns_repo.working_dir, "flaky_reruns.py"),
        "--flakefighters",
        "--active-flakefighters",
        "CosineSimilarity",
    )
    pytest_configure(config)

    plugin = config.pluginmanager.get_plugin("flakefighter_plugin")

    assert [f.__class__ for f in plugin.flakefighters] == [CosineSimilarity]
    assert [f.params() for f in plugin.flakefighters] == [
        {"run_live": False, "root": flaky_reruns_repo.working_dir, "threshold": 1}
    ]
