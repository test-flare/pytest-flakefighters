"""
Network-socket FlakeFighter.

This classifier identifies tests whose outcome changes when external
network access is disabled.

The normal pytest execution performed by pytest-flakefighters is used as
the baseline. If that execution passes, the same test is rerun in an
isolated pytest subprocess with socket access disabled using pytest-socket.

Local loopback hosts and Unix sockets remain allowed.

Classification rule:

    Normal execution PASS + network-blocked execution FAIL
        -> network-sensitive (flaky=True)

All other combinations
        -> flaky=False

The network-blocked rerun has a hard timeout so that tests which hang after
network access is disabled cannot hang pytest-flakefighters.
"""

import json
import os
import signal
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

    Uses the original pytest execution as the normal-network baseline.

    Tests that pass normally are rerun with external socket access disabled.
    If the same test fails under the network-blocked condition, the classifier
    records network sensitivity for that execution.

    Tests that already fail during the normal execution are not rerun because
    there is no PASS -> FAIL differential to observe.
    """

    DEFAULT_TIMEOUT = 10

    def __init__(
        self,
        run_live: bool,
        timeout: int = DEFAULT_TIMEOUT,
        extra_pytest_args: list[str] | None = None,
    ):
        super().__init__(run_live)

        if timeout <= 0:
            raise ValueError(
                "network classifier timeout must be greater than 0"
            )

        self.timeout = timeout
        self.extra_pytest_args = extra_pytest_args or []

    @classmethod
    def from_config(cls, config: dict):
        """
        Factory method used by pytest-flakefighters.
        """
        return cls(
            run_live=config.get("run_live", True),
            timeout=config.get(
                "network_classifier_timeout",
                cls.DEFAULT_TIMEOUT,
            ),
            extra_pytest_args=config.get(
                "network_classifier_extra_pytest_args",
                [],
            ),
        )

    def params(self):
        """
        Return parameters needed to reproduce this classifier instance.
        """
        return {
            "timeout": self.timeout,
            "extra_pytest_args": self.extra_pytest_args,
        }

    def _execution_nodeid(
        self,
        execution: TestExecution,
    ) -> str:
        """
        Get the pytest nodeid from a TestExecution.
        """
        return execution.test.name

    def _execution_should_be_rerun(
        self,
        execution: TestExecution,
    ) -> bool:
        """
        Only normally passing tests need the network-blocked experiment.

        The original pytest execution already represents the baseline
        network condition.

        We are specifically looking for:

            PASS normally -> FAIL with network blocked
        """
        return execution.outcome == "passed"

    def _find_matching_test_reports(
        self,
        report: dict[str, Any],
        test_nodeid: str,
    ) -> list[dict[str, Any]]:
        """
        Find pytest JSON report entries corresponding to this test.
        """
        tests = report.get("tests", [])

        if not isinstance(tests, list):
            return []

        exact_matches = [
            test
            for test in tests
            if isinstance(test, dict)
            and test.get("nodeid") == test_nodeid
        ]

        if exact_matches:
            return exact_matches

        # Fallback for cases where pytest modifies/extends the nodeid.
        return [
            test
            for test in tests
            if isinstance(test, dict)
            and str(test.get("nodeid", "")).startswith(test_nodeid)
        ]

    def _test_report_failed(
        self,
        test_report: dict[str, Any],
    ) -> bool:
        """
        Determine whether a test failed during the blocked-network rerun.

        pytest-json-report normally provides an overall `outcome` field.
        We also inspect setup/call/teardown as a fallback.
        """

        outcome = str(test_report.get("outcome", "")).lower()

        if outcome in {"failed", "error"}:
            return True

        if outcome in {"passed", "skipped", "xfailed", "xpassed"}:
            return False

        # Fallback: inspect individual pytest phases.
        for phase_name in ("setup", "call", "teardown"):
            phase = test_report.get(phase_name)

            if not isinstance(phase, dict):
                continue

            phase_outcome = str(
                phase.get("outcome", "")
            ).lower()

            if phase_outcome in {"failed", "error"}:
                return True

        return False

    def _terminate_process(
        self,
        process: subprocess.Popen,
    ) -> None:
        """
        Terminate a timed-out pytest subprocess.

        On POSIX systems the subprocess is placed into its own process group,
        allowing the classifier to terminate pytest and any child processes
        spawned by the test.
        """
        if process.poll() is not None:
            return

        try:
            if os.name == "posix":
                os.killpg(
                    os.getpgid(process.pid),
                    signal.SIGTERM,
                )
            else:
                process.terminate()

            try:
                process.wait(timeout=5)
                return
            except subprocess.TimeoutExpired:
                pass

            if os.name == "posix":
                os.killpg(
                    os.getpgid(process.pid),
                    signal.SIGKILL,
                )
            else:
                process.kill()

            process.wait()

        except ProcessLookupError:
            # Process already terminated.
            pass

    def _run_pytest_subprocess(
        self,
        command: list[str],
        test_nodeid: str,
    ) -> tuple[str, str] | None:
        """
        Execute the network-disabled pytest rerun.

        Returns:
            (stdout, stderr):
                subprocess completed within the timeout.

            None:
                subprocess exceeded the classifier timeout.

        A timeout is treated as inconclusive rather than as evidence of
        network sensitivity.
        """

        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
        }

        if os.name == "posix":
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen(
            command,
            **popen_kwargs,
        )

        try:
            stdout, stderr = process.communicate(
                timeout=self.timeout,
            )

            return stdout, stderr

        except subprocess.TimeoutExpired:
            self._terminate_process(process)

            # Drain remaining output after termination.
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                self._terminate_process(process)

            return None

    def _run_with_disabled_socket(
        self,
        test_nodeid: str,
    ) -> bool | None:
        """
        Rerun one test with external socket access disabled.

        Local loopback and Unix sockets remain allowed.

        Returns:
            True:
                The blocked-network rerun failed.

            False:
                The blocked-network rerun passed.

            None:
                The experiment was inconclusive, for example because the
                subprocess timed out or no usable test report was produced.
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = (
                Path(tmpdir)
                / "pytest_socket_report.json"
            )

            command = [
                sys.executable,
                "-m",
                "pytest",
                test_nodeid,

                # Prevent pytest-flakefighters from recursively running
                # inside the classifier subprocess.
                "-p",
                "no:pytest_flakefighters",

                # Disable external socket access.
                "--disable-socket",

                # Preserve local test infrastructure.
                "--allow-unix-socket",
                "--allow-hosts=localhost,127.0.0.1,::1",

                # Structured result used to determine PASS/FAIL.
                "--json-report",
                f"--json-report-file={report_path}",

                "-q",
            ]

            command.extend(
                self.extra_pytest_args
            )

            subprocess_result = (
                self._run_pytest_subprocess(
                    command,
                    test_nodeid,
                )
            )

            if subprocess_result is None:
                return None

            stdout, stderr = subprocess_result

            if not report_path.exists():
                return None

            try:
                with report_path.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    report = json.load(file)

            except (
                json.JSONDecodeError,
                OSError,
            ):
                return None

            matching_reports = (
                self._find_matching_test_reports(
                    report,
                    test_nodeid,
                )
            )

            if not matching_reports:
                return None

            # Normally there should only be one exact test report.
            # If pytest produced multiple matching entries, any failure
            # under the blocked condition counts as a blocked failure.
            for test_report in matching_reports:
                if self._test_report_failed(
                    test_report
                ):
                    return True

            return False

    def _flaky_execution(
        self,
        execution: TestExecution,
    ) -> bool:
        """
        Classify one execution using a differential network experiment.

        Classification:

            Original execution PASS
            +
            network-blocked rerun FAIL
            =
            True

        Every other result returns False.
        """

        # The main pytest execution is our normal-network baseline.
        if not self._execution_should_be_rerun(
            execution
        ):
            return False

        test_nodeid = self._execution_nodeid(
            execution
        )

        blocked_failed = (
            self._run_with_disabled_socket(
                test_nodeid
            )
        )

        # None means the experiment was inconclusive.
        if blocked_failed is None:
            return False

        return blocked_failed

    def flaky_test_live(
        self,
        execution: TestExecution,
    ):
        """
        Classify one test execution live.
        """
        execution.flakefighter_results.append(
            FlakefighterResult(
                name=self.__class__.__name__,
                flaky=self._flaky_execution(
                    execution
                ),
            )
        )

    def flaky_tests_post(
        self,
        run: Run,
    ):
        """
        Classify all executions after the full run.
        """
        for test in run.tests:
            for execution in test.executions:
                self.flaky_test_live(
                    execution
                )