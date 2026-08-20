"""
Network-sensitive test classifier.

Tests that pass normally are rerun with external network access blocked.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

from pytest_flakefighters.database_management import FlakefighterResult, Run, TestExecution
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter

SOCKET_BLOCKED_EXCEPTION_NAMES = ("SocketBlockedError", "SocketConnectBlockedError")

TIMEOUT_FAILURE_MARKER = "Timeout >"


class NetworkClassifier(FlakeFighter):
    """Classify tests that depend on external network access."""

    TIMEOUT_MULTIPLIER = 3
    MIN_TIMEOUT = 1.0

    def __init__(self, root: str = ".", extra_pytest_args: Optional[list[str]] = None):
        super().__init__(run_live=False)
        self.root = os.path.abspath(root)
        self.extra_pytest_args = extra_pytest_args or []

    @classmethod
    def from_config(cls, config: dict):
        return cls(
            root=config.get("root", "."), extra_pytest_args=config.get("extra_pytest_args", [])
        )

    def params(self):
        return {
            "root": self.root,
            "extra_pytest_args": self.extra_pytest_args,
            "timeout_multiplier": self.TIMEOUT_MULTIPLIER,
            "minimum_timeout": self.MIN_TIMEOUT,
        }

    def flaky_test_live(self, execution):
        raise NotImplementedError("NetworkClassifier only supports postprocessing classification")

    def _longest_passed_duration(self, test) -> Optional[float]:
        """Return the longest successful execution duration."""
        durations = []

        for execution in test.executions:
            if execution.outcome != "passed":
                continue

            if execution.start_time is None or execution.end_time is None:
                continue

            duration = (execution.end_time - execution.start_time).total_seconds()

            if duration >= 0:
                durations.append(duration)

        return max(durations) if durations else None

    def _compute_timeout(self, durations: list[float]) -> float:
        """Compute one timeout for all eligible tests."""
        longest = max(durations) if durations else 0.0

        return max(self.MIN_TIMEOUT, longest * self.TIMEOUT_MULTIPLIER)

    @staticmethod
    def _load_report(report_path: Path) -> Optional[dict[str, Any]]:
        """Load a pytest JSON report."""
        try:
            with report_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _report_duration(test_report: dict[str, Any]) -> Optional[float]:
        """Return total duration for a successful test report."""
        outcome = str(test_report.get("outcome", "")).lower()

        if outcome != "passed":
            return None

        total = 0.0

        for phase_name in ("setup", "call", "teardown"):
            phase = test_report.get(phase_name)

            if not isinstance(phase, dict):
                continue

            phase_duration = phase.get("duration")

            if isinstance(phase_duration, (int, float)):
                total += phase_duration

        return total

    def _measure_own_baseline(self, nodeids: list[str]) -> dict[str, dict[str, Any]]:
        """Run missing tests normally."""
        if not nodeids:
            return {}

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "network_baseline_report.json"

            command = [
                sys.executable,
                "-m",
                "pytest",
                *nodeids,
                "-p",
                "no:flakefighters",
                "--json-report",
                f"--json-report-file={report_path}",
                "-q",
                *self.extra_pytest_args,
            ]

            completed = self._run_pytest_subprocess(
                command, cwd=self.root, env=self._subprocess_env()
            )

            if not completed or not report_path.exists():
                return {}

            report = self._load_report(report_path)

            if report is None:
                return {}

            tests = report.get("tests", [])

            if not isinstance(tests, list):
                return {}

            measured = {}

            for test_report in tests:
                if not isinstance(test_report, dict):
                    continue

                nodeid = test_report.get("nodeid")

                if not nodeid:
                    continue

                outcome = str(test_report.get("outcome", "")).lower()

                measured[nodeid] = {
                    "outcome": outcome,
                    "duration": self._report_duration(test_report),
                    "report": test_report,
                }

            return measured

    def _report_text(self, test_report: dict[str, Any]) -> str:
        """Combine report failure text."""
        parts = [str(test_report.get("longrepr", ""))]

        for phase_name in ("setup", "call", "teardown"):
            phase = test_report.get(phase_name)

            if not isinstance(phase, dict):
                continue

            parts.append(str(phase.get("longrepr", "")))

            crash = phase.get("crash", {})

            if isinstance(crash, dict):
                parts.append(str(crash.get("message", "")))

        return "\n".join(parts)

    def _report_confirms_socket_blocked(self, test_report: dict[str, Any]) -> bool:
        text = self._report_text(test_report)

        return any(name in text for name in SOCKET_BLOCKED_EXCEPTION_NAMES)

    def _report_confirms_timeout(self, test_report: dict[str, Any]) -> bool:
        return TIMEOUT_FAILURE_MARKER in self._report_text(test_report)

    def _report_failed(self, test_report: dict[str, Any]) -> bool:
        outcome = str(test_report.get("outcome", "")).lower()

        if outcome in {"failed", "error"}:
            return True

        for phase_name in ("setup", "call", "teardown"):
            phase = test_report.get(phase_name)

            if not isinstance(phase, dict):
                continue

            phase_outcome = str(phase.get("outcome", "")).lower()

            if phase_outcome in {"failed", "error"}:
                return True

        return False

    def _subprocess_env(self) -> dict[str, str]:
        """Build child process environment."""
        env = os.environ.copy()
        env.pop("PYTEST_ADDOPTS", None)
        env.pop("COVERAGE_FILE", None)
        return env

    def _run_pytest_subprocess(self, command: list[str], cwd: str, env: dict[str, str]) -> bool:
        """Run a child pytest process."""
        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=cwd,
                env=env,
                check=False,
            )
            return True
        except OSError:
            return False

    def _run_with_disabled_socket(
        self, nodeids: list[str], per_test_timeout: float
    ) -> Optional[dict[str, dict[str, Any]]]:
        """Run eligible tests with external sockets disabled."""
        if not nodeids:
            return {}

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "network_report.json"

            command = [
                sys.executable,
                "-m",
                "pytest",
                *nodeids,
                "-p",
                "no:flakefighters",
                "--disable-socket",
                "--allow-unix-socket",
                "--allow-hosts=localhost,127.0.0.1,::1",
                f"--timeout={per_test_timeout}",
                "--json-report",
                f"--json-report-file={report_path}",
                "-q",
                *self.extra_pytest_args,
            ]

            completed = self._run_pytest_subprocess(
                command, cwd=self.root, env=self._subprocess_env()
            )

            if not completed or not report_path.exists():
                return None

            report = self._load_report(report_path)

            if report is None:
                return None

            tests = report.get("tests", [])

            if not isinstance(tests, list):
                return None

            return {
                test_report["nodeid"]: test_report
                for test_report in tests
                if (isinstance(test_report, dict) and test_report.get("nodeid"))
            }

    def _collect_existing_baselines(self, run: Run):
        """Separate existing passing tests from tests needing a baseline."""
        eligible_tests = []
        missing_tests = []
        durations = []

        for test in run.tests:
            if not test.executions:
                missing_tests.append(test)
                continue

            has_pass = any(execution.outcome == "passed" for execution in test.executions)

            if not has_pass:
                continue

            eligible_tests.append(test)

            duration = self._longest_passed_duration(test)

            if duration is not None:
                durations.append(duration)

        return (eligible_tests, missing_tests, durations)

    def _add_missing_baselines(self, missing_tests, eligible_tests, durations):
        """Measure and store baselines for tests with no executions."""
        if not missing_tests:
            return

        measured = self._measure_own_baseline([test.name for test in missing_tests])

        for test in missing_tests:
            baseline = measured.get(test.name)

            if baseline is None:
                continue

            execution = TestExecution(
                outcome=baseline["outcome"], report=json.dumps(baseline["report"])
            )

            test.executions.append(execution)

            if baseline["outcome"] != "passed":
                continue

            eligible_tests.append(test)

            if baseline["duration"] is not None:
                durations.append(baseline["duration"])

    def _store_blocked_results(self, eligible_tests, blocked_reports):
        """Store classifications from blocked-network reports."""
        for test in eligible_tests:
            report = blocked_reports.get(test.name)

            if report is None:
                continue

            if self._report_confirms_timeout(report):
                continue

            network_sensitive = self._report_failed(
                report
            ) and self._report_confirms_socket_blocked(report)

            result = FlakefighterResult(name=self.__class__.__name__, flaky=network_sensitive)

            if result not in test.flakefighter_results:
                test.flakefighter_results.append(result)

    def flaky_tests_post(self, run: Run):
        """Classify tests after the normal pytest run."""
        if not run.tests:
            return

        (eligible_tests, missing_tests, durations) = self._collect_existing_baselines(run)

        self._add_missing_baselines(missing_tests, eligible_tests, durations)

        if not eligible_tests:
            return

        per_test_timeout = self._compute_timeout(durations)

        blocked_reports = self._run_with_disabled_socket(
            [test.name for test in eligible_tests], per_test_timeout
        )

        if blocked_reports is None:
            return

        self._store_blocked_results(eligible_tests, blocked_reports)
