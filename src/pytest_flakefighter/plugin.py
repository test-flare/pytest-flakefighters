"""
This module implements the DeFlaker algorithm [Bell et al. 10.1145/3180155.3180164] as a pytest plugin.
"""

import os

import coverage
import git
import pytest
from unidiff import PatchSet


class FlakeFighter:
    """
    Flakefighter plugin class implements the DeFlaker algorithm.
    """

    def __init__(
        self,
        repo_root: str = None,
        target_commit: str = None,
        source_commit: str = None,
    ):
        self.cov = coverage.Coverage()
        self.repo = git.Repo(repo_root if repo_root is not None else ".")
        self.lines_changed = {}
        if target_commit is None and not self.repo.is_dirty():
            # No uncommitted changes, so use most recent commit
            self.target_commit = self.repo.commit().hexsha
        else:
            self.target_commit = target_commit
        if source_commit is None:
            if self.target_commit is None:
                # If uncommitted changes, use most recent commit as source
                self.source_commit = self.repo.commit().hexsha
            else:
                # If no uncommitted changes, use previous commit as source
                parents = [
                    commit.hexsha
                    for commit in self.repo.commit(source_commit).iter_parents()
                    if commit.hexsha != self.target_commit
                ]
                self.source_commit = parents[0]
        else:
            self.source_commit = source_commit

        patches = PatchSet(self.repo.git.diff(self.source_commit, self.target_commit, "-U0", "--no-prefix"))
        for patch in patches:
            if patch.target_file == patch.source_file:
                abspath = os.path.join(self.repo.working_dir, patch.source_file)
                self.lines_changed[abspath] = []
                for hunk in patch:
                    # Add each line in the hunk to lines_changed
                    self.lines_changed[abspath] += list(
                        range(hunk.target_start, hunk.target_start + hunk.target_length + 1)
                    )
        print("LINES CHANGED", self.lines_changed)

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
        self.cov.start()
        # Lines cannot appear as covered on our tests because the coverage measurement is leaking into the self.cov
        self.cov.switch_context(item.nodeid)
        yield
        self.cov.stop()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(
        self, item: pytest.Item, call: pytest.CallInfo[None]  # pylint: disable=unused-argument
    ) -> pytest.TestReport:
        """
        Classify failed tests as flaky if they don't cover any changed code.

        :param item: The item.
        :param call: The :class:`~pytest.CallInfo` for the phase.

        :return: The modified test report.
        """
        outcome = yield
        report = outcome.get_result()
        if report.when == "call" and report.failed:
            line_coverage = self.cov.get_data()
            flaky = not any(
                self.line_modified_by_latest_commit(file_path, line_number)
                for file_path in line_coverage.measured_files()
                for line_number in line_coverage.lines(file_path)
                if file_path in self.lines_changed
            )
            report.flaky = flaky
            item.user_properties.append(("flaky", flaky))
            self.genuine_failure_observed = not flaky
        return report

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

    def line_modified_by_latest_commit(self, file_path: str, line_number: int) -> bool:
        """
        Returns true if the given line in the file has been modified by the present commit.

        :param file_path: The file to check.
        :param line_number: The line number to check.
        """
        print("FILEPATH", file_path, ":", line_number)
        if line_number in self.lines_changed[file_path]:
            return self.lines_changed[file_path][line_number]
        return True

    def pytest_sessionfinish(
        self,
        session: pytest.Session,
        exitstatus: pytest.ExitCode,  # pylint: disable=unused-argument
    ) -> None:
        """Called after whole test run finished, right before returning the exit status to the system.
        :param session: The pytest session object.
        :param exitstatus: The status which pytest will return to the system.
        """
        if (
            session.config.option.suppress_flaky
            and session.exitstatus == pytest.ExitCode.TESTS_FAILED
            and not self.genuine_failure_observed
        ):
            session.exitstatus = pytest.ExitCode.OK


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
        dest="repo_path",
        default=None,
        help="The commit hash to compare against.",
    )
    group.addoption(
        "--suppress-flaky-failures-exit-code",
        action="store_true",
        dest="suppress_flaky",
        default=False,
        help="Return OK exit code if the only failures are flaky failures.",
    )


def pytest_configure(config: pytest.Config):
    """
    Initialise the FlakeFighter class.
    :param config: The config options.
    """
    config.pluginmanager.register(
        FlakeFighter(config.option.repo_path, config.option.target_commit, config.option.source_commit)
    )
