"""
Network-socket FlakeFighter.

This classifier reruns a failed pytest test with socket access disabled
using pytest-socket.

If the rerun report contains SocketBlockedError, the classifier records
network/socket evidence for that test.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    TestExecution,
)
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter


class NetworkClassifier(FlakeFighter):
    """
    Network/socket FlakeFighter.

    Given a failed test execution, this classifier reruns the same test with
    pytest-socket using --disable-socket.

    If SocketBlockedError is found, this classifier records evidence that the
    test attempted socket access when sockets were disabled.
    """

    SOCKET_MARKER = "SocketBlockedError"

    def __init__(
        self,
        run_live: bool,
        timeout: int = 120,
        extra_pytest_args: list[str] | None = None,
    ):
        super().__init__(run_live)
        self.timeout = timeout
        self.extra_pytest_args = extra_pytest_args or []

    @classmethod
    def from_config(cls, config: dict):
        """
        Factory method used by pytest-flakefighters.
        """
        return cls(
            run_live=config.get("run_live", True),
            timeout=config.get("network_classifier_timeout", 120),
            extra_pytest_args=config.get("network_classifier_extra_pytest_args", []),
        )

    def params(self):
        """
        Return parameters needed to reproduce this classifier instance.
        """
        return {
            "timeout": self.timeout,
            "extra_pytest_args": self.extra_pytest_args,
        }

    def _execution_nodeid(self, execution: TestExecution) -> str:
        """
        Get pytest nodeid from a TestExecution.
        """
        return execution.test.name

    def _execution_should_be_rerun(self, execution: TestExecution) -> bool:
        """
        Return whether this execution should be rerun with sockets disabled.
        """
        return execution.outcome in {"failed", "error"}

    def _phase_contains_socket_blocked_error(self, phase: dict[str, Any]) -> bool:
        """
        Check one pytest phase: setup, call, or teardown.
        """

        if not isinstance(phase, dict):
            return False

        crash = phase.get("crash", {})
        if isinstance(crash, dict):
            crash_message = str(crash.get("message", ""))
            if self.SOCKET_MARKER in crash_message:
                return True

        longrepr = str(phase.get("longrepr", ""))
        if self.SOCKET_MARKER in longrepr:
            return True

        traceback = phase.get("traceback", [])
        if isinstance(traceback, list):
            for frame in traceback:
                if not isinstance(frame, dict):
                    continue

                frame_message = str(frame.get("message", ""))
                if self.SOCKET_MARKER in frame_message:
                    return True

        return False

    def _test_report_contains_socket_blocked_error(
        self,
        test_report: dict[str, Any],
    ) -> bool:
        """
        Check setup, call, and teardown for SocketBlockedError.
        """

        for phase_name in ("setup", "call", "teardown"):
            phase = test_report.get(phase_name, {})
            if self._phase_contains_socket_blocked_error(phase):
                return True

        return False

    def _find_matching_test_reports(
        self,
        report: dict[str, Any],
        test_nodeid: str,
    ) -> list[dict[str, Any]]:
        """
        Find the pytest JSON report entries for this test.
        """

        tests = report.get("tests", [])
        if not isinstance(tests, list):
            return []

        exact_matches = [
            test
            for test in tests
            if isinstance(test, dict) and test.get("nodeid") == test_nodeid
        ]

        if exact_matches:
            return exact_matches

        return [
            test
            for test in tests
            if isinstance(test, dict)
            and str(test.get("nodeid", "")).startswith(test_nodeid)
        ]

    def _run_with_disabled_socket(self, test_nodeid: str) -> bool:
        """
        Rerun the test with all socket access disabled.

        Returns:
            True if SocketBlockedError is found.
            False otherwise.
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "pytest_socket_report.json"

            command = [
                sys.executable,
                "-m",
                "pytest",
                test_nodeid,
                "-p",
                "no:pytest_flakefighters",
                "--disable-socket",
                "--json-report",
                f"--json-report-file={report_path}",
                "-q",
            ]

            command.extend(self.extra_pytest_args)

            try:
                completed = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.timeout,
                )
            except subprocess.TimeoutExpired:
                return False

            if report_path.exists():
                try:
                    with report_path.open("r", encoding="utf-8") as file:
                        report = json.load(file)

                    matching_reports = self._find_matching_test_reports(
                        report,
                        test_nodeid,
                    )

                    for test_report in matching_reports:
                        if self._test_report_contains_socket_blocked_error(test_report):
                            return True

                except json.JSONDecodeError:
                    pass

            combined_output = f"{completed.stdout}\n{completed.stderr}"
            return self.SOCKET_MARKER in combined_output

    def _flaky_execution(self, execution: TestExecution) -> bool:
        """
        Classify one execution.

        Passing/skipped executions are not rerun and return False.
        Failed/error executions are rerun with sockets disabled.
        """

        if not self._execution_should_be_rerun(execution):
            return False

        test_nodeid = self._execution_nodeid(execution)
        return self._run_with_disabled_socket(test_nodeid)

    def flaky_test_live(self, execution: TestExecution):
        """
        Classify one test execution live.
        """

        execution.flakefighter_results.append(
            FlakefighterResult(
                name=self.__class__.__name__,
                flaky=self._flaky_execution(execution),
            )
        )

    def flaky_tests_post(self, run: Run):
        """
        Classify test executions after the full run.
        """

        for test in run.tests:
            for execution in test.executions:
                self.flaky_test_live(execution)