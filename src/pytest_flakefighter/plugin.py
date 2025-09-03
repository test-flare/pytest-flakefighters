"""
This module implements the DeFlaker algorithm [Bell et al. 10.1145/3180155.3180164] as a pytest plugin.
"""

import pytest
import coverage
import git


class FlakeFighter:
    def __init__(self, repo_root: str = None, commit: str = None):
        self.failed_reports = {}
        self.cov = coverage.Coverage()
        self.repo = git.Repo(repo_root if repo_root is not None else ".")
        if commit is not None:
            self.commit = commit
        else:
            self.commit = self.repo.head.commit.hexsha
        for commit in self.repo.iter_commits(max_count=10):
            print("HASH", commit.hexsha, commit.summary)
        print("COMMIT", self.commit)

    def pytest_runtest_logreport(self, report: pytest.TestReport):
        """
        Stores the failed reports in a global list.

        :param report: Pytest report for a test case.
        """
        if report.when == "setup":
            self.cov.erase()
            self.cov.start()
        if report.when == "call" and report.failed:
            self.cov.stop()
            line_coverage = self.cov.get_data()
            self.failed_reports[report] = {
                filename: line_coverage.lines(filename) for filename in line_coverage.measured_files()
            }

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
        real_faults = []
        for report, line_coverage in self.failed_reports.items():
            for file_path, lines in line_coverage.items():
                if any(self.line_modified_by_latest_commit(file_path, line) for line in lines):
                    real_faults.append(report.nodeid)
        print()
        print("Real faults", real_faults)


def pytest_addoption(parser):
    group = parser.getgroup("flakefighter")
    group.addoption(
        "--commit", action="store", dest="commit_hash", default=None, help="The commit hash to compare against."
    )
    group.addoption(
        "--repo", action="store", dest="repo_path", default=None, help="The commit hash to compare against."
    )


def pytest_configure(config):
    config.pluginmanager.register(FlakeFighter(config.option.repo_path, config.option.commit_hash))
