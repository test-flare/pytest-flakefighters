"""
This module implements the DeFlaker algorithm [Bell et al. 10.1145/3180155.3180164] as a pytest plugin.
"""

import os

import coverage
import git
import pytest


class FlakeFighter:
    """
    Flakefighter plugin class implements the DeFlaker algorithm.
    """

    def __init__(self, repo_root: str = None, commit: str = None):
        self.cov = coverage.Coverage()
        self.repo = git.Repo(repo_root if repo_root is not None else ".")
        if commit is not None:
            self.commit = commit
        else:
            self.commit = self.repo.head.commit.hexsha
        root = self.repo.git.rev_parse("--show-toplevel")
        self.lines_changed = {
            os.path.abspath(os.path.join(root, file)): {} for file in self.repo.commit(self.commit).stats.files
        }
        self.genuine_failure_observed = False

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
            if not any(
                self.line_modified_by_latest_commit(file_path, line_number)
                for file_path in line_coverage.measured_files()
                for line_number in line_coverage.lines(file_path)
                if file_path in self.lines_changed
            ):
                report.flaky = True
            else:
                self.genuine_failure_observed = True
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
        if line_number in self.lines_changed[file_path]:
            return self.lines_changed[file_path][line_number]
        output = self.repo.git.log("-L", f"{line_number},{line_number}:{file_path}")
        self.lines_changed[file_path][line_number] = f"commit {self.commit}" in output
        return self.lines_changed[file_path][line_number]

    def pytest_sessionfinish(
        self,
        session: pytest.Session,
        exitstatus: pytest.ExitCode,  # pylint: disable=unused-argument
    ) -> None:
        """Called after whole test run finished, right before returning the exit status to the system.
        :param session: The pytest session object.
        :param exitstatus: The status which pytest will return to the system.
        """
        print("\nSTATUS", session.config.option.suppress_flaky, not self.genuine_failure_observed)
        if session.config.option.suppress_flaky and not self.genuine_failure_observed:
            session.exitstatus = pytest.ExitCode.OK


def pytest_addoption(parser: pytest.Parser):
    """
    Add extra pytest options.
    :param parser: The argument parser.
    """
    group = parser.getgroup("flakefighter")
    group.addoption(
        "--commit",
        action="store",
        dest="commit_hash",
        default=None,
        help="The commit hash to compare against.",
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
    config.pluginmanager.register(FlakeFighter(config.option.repo_path, config.option.commit_hash))
