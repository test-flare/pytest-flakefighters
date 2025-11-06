"""
This module implements the DeFlaker algorithm [Bell et al. 10.1145/3180155.3180164] as a pytest plugin.
"""

from datetime import datetime
from typing import Union

import coverage
import pytest
from _pytest.runner import runtestprotocol

from pytest_flakefighters.database_management import Database, Run, Test, TestExecution
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter
from pytest_flakefighters.flakefighters.coverage_independence import (
    CoverageIndependence,
)
from pytest_flakefighters.flakefighters.deflaker import DeFlaker
from pytest_flakefighters.function_coverage import Profiler


class FlakeFighterPlugin:  # pylint: disable=R0902
    """
    The main plugin to manage the various FlakeFighter tools.
    """

    def __init__(  # pylint: disable=R0913,R0917
        self,
        database: Database,
        cov: Union[coverage.Coverage, Profiler],
        flakefighters: list[FlakeFighter],
        source_commit: str = None,
        target_commit: str = None,
        load_max_runs: int = None,
        save_run: bool = True,
        max_flaky_reruns: int = 0,
    ):
        self.cov = cov
        self.genuine_failure_observed = False
        self.save_run = save_run
        self.database = database
        self.flakefighters = flakefighters
        self.source_commit = source_commit
        self.target_commit = target_commit
        self.max_flaky_reruns = max_flaky_reruns

        self.run = Run(source_commit=self.source_commit, target_commit=self.target_commit)
        self.previous_runs = self.database.load_runs(load_max_runs)

    def pytest_sessionstart(self, session: pytest.Session):  # pylint: disable=unused-argument
        """
        Start the coverage measurement before tests are collected so we measure class and method definitions as covered.
        :param session: The session.
        """
        self.cov.start()

    def pytest_collection_finish(self, session: pytest.Session):  # pylint: disable=unused-argument
        """
        Stop the coverage measurement after tests are collected.
        :param session: The session.
        """
        # Line cannot appear as covered on our tests because the coverage measurement is leaking into the self.cov
        self.cov.stop()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item: pytest.Item):
        """
        Start the coverage measurement and label the coverage for the current test, run the test,
        then stop coverage measurement.

        :param item: The item.
        """
        item.start = datetime.now().timestamp()
        self.cov.start()
        # Lines cannot appear as covered on our tests because the coverage measurement is leaking into the self.cov
        self.cov.switch_context(item.nodeid)
        yield
        self.cov.stop()
        item.stop = datetime.now().timestamp()

    def pytest_runtest_protocol(self, item: pytest.Item, nextitem: pytest.Item) -> bool:
        """
        Rerun flaky tests. Follows a similar control logic to the pytest-rerunfailures plugin.

        :param item: The item.
        :param nextitem: The next item.

        :return: The return value is not used, but only stops further processing.
        """
        item.execution_count = 0
        executions = []
        skipped = False

        for _ in range(self.max_flaky_reruns + 1):
            item.execution_count += 1
            item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
            reports = runtestprotocol(item, nextitem=nextitem, log=False)

            for report in reports:  # up to 3 reports: setup, call, teardown
                if report.when == "setup" and report.skipped:
                    skipped = True
                if report.when == "call":
                    line_coverage = self.cov.get_data()
                    line_coverage.set_query_context(item.nodeid)
                    captured_output = dict(report.sections)
                    test_execution = TestExecution(
                        outcome=report.outcome,
                        stdout=captured_output.get("stdout"),
                        stderr=captured_output.get("stderr"),
                        stack_trace=str(report.longrepr),
                        start_time=datetime.fromtimestamp(item.start),
                        end_time=datetime.fromtimestamp(item.stop),
                        coverage={
                            file_path: line_coverage.lines(file_path) for file_path in line_coverage.measured_files()
                        },
                    )
                    executions.append(test_execution)
                    for ff in filter(lambda ff: ff.run_live, self.flakefighters):
                        ff.flaky_test_live(test_execution)
                    report.flaky = any(result.flaky for result in test_execution.flakefighter_results)
                    self.genuine_failure_observed = self.genuine_failure_observed or (
                        report.failed and not report.flaky
                    )
                    if (
                        item.execution_count <= self.max_flaky_reruns
                        and report.flaky
                        and not report.passed  # not equivalent to report.failed because it could error
                    ):
                        break  # trigger rerun
                item.ihook.pytest_runtest_logreport(report=report)
            else:
                break  # Skip further reruns

        item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
        test = Test(  # pylint: disable=E1123
            name=item.nodeid,
            skipped=skipped,
            executions=executions,
        )
        self.run.tests.append(test)
        return True

    def pytest_report_teststatus(
        self, report: pytest.TestReport, config: pytest.Config  # pylint: disable=unused-argument
    ) -> tuple[str, str, str]:
        """
        Report flaky failures as such.
        :param report: The report object whose status is to be returned.
        :param config: The pytest config object.
        :returns: The test status.
        """
        if getattr(report, "flaky", False):
            return report.outcome, "F", ("FLAKY", {"yellow": True})
        return None

    def pytest_sessionfinish(
        self,
        session: pytest.Session,
        exitstatus: pytest.ExitCode,  # pylint: disable=unused-argument
    ) -> None:
        """Called after whole test run finished, right before returning the exit status to the system.
        :param session: The pytest session object.
        :param exitstatus: The status which pytest will return to the system.
        """
        for ff in filter(lambda ff: not ff.run_live, self.flakefighters):
            ff.flaky_tests_post(self.run)

        if (
            session.config.option.suppress_flaky
            and session.exitstatus == pytest.ExitCode.TESTS_FAILED
            and not self.genuine_failure_observed
        ):
            session.exitstatus = pytest.ExitCode.OK

        if self.save_run:
            self.database.save(self.run)
        self.database.engine.dispose()


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
