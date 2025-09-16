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
        self.cov.start()
        self.repo = git.Repo(repo_root if repo_root is not None else ".")
        if commit is not None:
            self.commit = commit
        else:
            self.commit = self.repo.head.commit.hexsha
        root = self.repo.git.rev_parse("--show-toplevel")
        self.lines_changed = {
            os.path.abspath(os.path.join(root, file)): {} for file in self.repo.commit(self.commit).stats.files
        }

    def pytest_report_teststatus(self, report: pytest.TestReport):
        """
        Classify tests as flaky failures if they did not execute any changed code.

        :param report: The pytest report object.
        """
        if report.when == "setup":
            self.cov.switch_context(report.nodeid)
        if report.when == "call" and report.failed:
            line_coverage = self.cov.get_data()
            line_coverage.set_query_context(report.nodeid)
            if not any(
                self.line_modified_by_latest_commit(file_path, line_number)
                for file_path in line_coverage.measured_files()
                for line_number in line_coverage.lines(file_path)
                if file_path in self.lines_changed
            ):
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
