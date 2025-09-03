import os
import subprocess
import pytest
import coverage


class FlakeFighter:
    def __init__(self, commit: str = None):
        self.failed_reports = {}
        self.cov = coverage.Coverage()
        if commit is not None:
            self.commit = commit
        else:
            self.commit = subprocess.check_output("git rev-parse HEAD", shell=True).decode("utf-8").strip()

    def pytest_runtest_logreport(self, report: pytest.TestReport):
        """
        Stores the failed reports in a global list.

        :param report: Pytest report for a test case.
        """
        if report.when == "setup":
            # self.cov.erase()
            self.cov.start()
        if report.when == "call" and report.failed:
            self.cov.stop()
            line_coverage = self.cov.get_data()
            self.failed_reports[report] = {
                filename: line_coverage.lines(filename) for filename in line_coverage.measured_files()
            }

    def line_modified_by_latest_commit(self, file_path, line_number):
        try:
            output = subprocess.check_output(
                f"git log -L {line_number},{line_number}:{file_path}", shell=True, stderr=subprocess.DEVNULL
            ).decode("utf-8")
            if f"commit {self.commit}" in output:
                return True
        except subprocess.CalledProcessError:
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
        print(real_faults)


def pytest_configure(config):
    config.pluginmanager.register(FlakeFighter())
