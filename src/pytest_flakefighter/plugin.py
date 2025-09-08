"""
This module implements the DeFlaker algorithm [Bell et al. 10.1145/3180155.3180164] as a pytest plugin.
"""

import coverage
import git
import pytest


class FlakeFighter:
    """
    Flakefighter plugin class implements the DeFlaker algorithm.
    """

    def __init__(self, repo_root: str = None, commit: str = None):
        self.cov = coverage.Coverage()
        self.cov.start()
        self.repo = git.Repo(repo_root if repo_root is not None else ".")
        self.real_faults = []
        if commit is not None:
            self.commit = commit
        else:
            self.commit = self.repo.head.commit.hexsha

    def pytest_runtest_logreport(self, report: pytest.TestReport):
        """
        Stores the failed reports in a global list.

        :param report: Pytest report for a test case.
        """
        if report.when == "setup":
            self.cov.switch_context(report.nodeid)
        if report.when == "call" and report.failed:
            line_coverage = self.cov.get_data()
            for filename in line_coverage.measured_files():
                lines_by_context = line_coverage.contexts_by_lineno(filename)
                if any(
                    report.nodeid in contexts and self.line_modified_by_latest_commit(filename, line)
                    for line, contexts in lines_by_context.items()
                ):
                    self.real_faults.append(report.nodeid)

    def line_modified_by_latest_commit(self, file_path: str, line_number: int) -> bool:
        """
        Returns true if the given line in the file has been modified by the present commit.

        :param file_path: The file to check.
        :param line_number: The line number to check.
        """
        try:
            output = self.repo.git.log("-L", f"{line_number},{line_number}:{file_path}")
            if f"commit {self.commit}" in output:
                return True
        except git.exc.GitCommandError:
            return False
        return False

    def pytest_sessionfinish(self):
        """
        Called after the entire test session finishes.
        Accesses the global list of failed reports.
        """
        print()
        print("Real faults", self.real_faults)


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


def pytest_configure(config: pytest.Config):
    """
    Initialise the FlakeFighter class.
    :param config: The config options.
    """
    config.pluginmanager.register(FlakeFighter(config.option.repo_path, config.option.commit_hash))
