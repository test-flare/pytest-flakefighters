"""
Network-classifier FlakeFighter.

This classifier identifies tests whose outcome changes when external network access is
disabled. Only tests that passed in the normal run are rerun with network access blocked

Classification is performed based on the following rule:

    Normal-run PASS + network-blocked-run FAIL, where the blocked-run failure is confirmed
    to be caused by a blocked socket operation (pytest_socket.SocketBlockedError or
    pytest_socket.SocketConnectBlockedError)
        -> network-sensitive (flaky=True)
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

from pytest_flakefighters.database_management import FlakefighterResult, Run
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter

# : The exception names raised by pytest-socket when a blocked socket operation is attempted.
SOCKET_BLOCKED_EXCEPTION_NAMES = ("SocketBlockedError", "SocketConnectBlockedError")


class NetworkClassifier(FlakeFighter):
    """
    Detect tests that depend on external network access.

    Baseline-passing tests are rerun with external sockets disabled.
    A test is classified as network sensitive when the blocked rerun
    fails because of a pytest socket blocked socket exception.
    """
    DEFAULT_TIMEOUT = 30

	 # The subprocess needs this because it must execute pytest inside the subject project's directory
    def __init__(
        self,
        timeout: int=DEFAULT_TIMEOUT,
        root: str=".",
        extra_pytest_args: Optional[list[str]]=None,
    ):
        super().__init__(run_live=False)

        if timeout <= 0:
            raise ValueError("network classifier timeout must be greater than 0")

        self.timeout = timeout
        self.root = os.path.abspath(root)
        self.extra_pytest_args = extra_pytest_args or []

    @classmethod
    def from_config(cls, config: dict):

        return cls(
            timeout=config.get("network_classifier_timeout", cls.DEFAULT_TIMEOUT),
            root=config.get("root", "."),
            extra_pytest_args=config.get("extra_pytest_args", []),
        )

    def params(self):

        return {
            "timeout": self.timeout,
            "root": self.root,
            "extra_pytest_args": self.extra_pytest_args,
        }

    def flaky_test_live(self, execution):
        """
        NOT SUPPORTED.
        This classifier needs the whole suite's baseline results before it can compare
        anything, so it only supports postprocessing classification.
        :param execution: The test execution to classify.
        """
        raise NotImplementedError("NetworkClassifier only supports postprocessing classification")

    def _report_confirms_socket_blocked(self, test_report: dict[str, Any]) -> bool:
        """
        Confirm that a failure was specifically caused by a blocked socket operation, by
        checking for one of pytest-socket's exception names in the rendered failure text of
        any phase.
        """
        for phase_name in ("setup", "call", "teardown"):
            phase = test_report.get(phase_name)
            if not isinstance(phase, dict):
                continue
            longrepr = phase.get("longrepr", "")
            crash = phase.get("crash", {})
            crash_message = crash.get("message", "") if isinstance(crash, dict) else ""
            haystack = str(longrepr) + str(crash_message)
            if any(name in haystack for name in SOCKET_BLOCKED_EXCEPTION_NAMES):
                return True

        top_level_longrepr = str(test_report.get("longrepr", ""))
        return any(name in top_level_longrepr for name in SOCKET_BLOCKED_EXCEPTION_NAMES)

    def _test_report_confirmed_flaky(self, test_report: dict[str, Any]) -> bool:
        """
        Determine whether a test failed during the blocked-network run, specifically due to a
        blocked socket operation.
        """
        outcome = str(test_report.get("outcome", "")).lower()

        failed = outcome in {"failed", "error"} or any(
            str(test_report.get(phase, {}).get("outcome", "")).lower() in {"failed", "error"}
            for phase in ("setup", "call", "teardown")
            if isinstance(test_report.get(phase), dict)
        )

        if not failed:
            return False

        return self._report_confirms_socket_blocked(test_report)

    def _terminate_process(self, process: subprocess.Popen) -> None:
        """
        Terminate a timed-out pytest subprocess.
        """
        if process.poll() is not None:
            return

        try:
            if os.name == "posix":
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()

            try:
                process.wait(timeout=5)
                return
            except subprocess.TimeoutExpired:
                pass

            if os.name == "posix":
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()

            process.wait()

        except ProcessLookupError:
            # Process already terminated.
            pass

    def _run_pytest_subprocess(
        self,
        command: list[str],
        cwd: str,
        env: dict[str, str],
    ) -> Optional[dict[str, dict[str, Any]]]:
        """
        Execute the network-disabled pytest rerun.

        :return: (stdout, stderr) if the subprocess completed within the timeout, else None if
            the subprocess exceeded the classifier timeout.
        """
        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "cwd": cwd,
            "env": env,
        }

        if os.name == "posix":
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen(command, **popen_kwargs)  # pylint: disable=R1732

        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
            return stdout, stderr

        except subprocess.TimeoutExpired:
            self._terminate_process(process)

            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                self._terminate_process(process)

            return None

    def _subprocess_env(self) -> dict[str, str]:

        env = os.environ.copy()
        env.pop("PYTEST_ADDOPTS", None)
        env.pop("COVERAGE_FILE", None)
        return env

    def _run_with_disabled_socket(self, nodeids: list[str]) -> Optional[dict[str, dict[str, Any]]]:

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "pytest_socket_report.json"

            command = [
                sys.executable,
                "-m",
                "pytest",
                *nodeids,
                "-p",
                "no:flakefighters",
                # Disable external socket access.
                "--disable-socket",
                # Preserve local test infrastructure.
                "--allow-unix-socket",
                "--allow-hosts=localhost,127.0.0.1,::1",
                # Structured result used to determine PASS/FAIL and confirm the failure cause.
                "--json-report",
                f"--json-report-file={report_path}",
                "-q",
            ]

            command.extend(self.extra_pytest_args)

            subprocess_result = self._run_pytest_subprocess(
                command,
                cwd=self.root,
                env=self._subprocess_env(),
            )

            if subprocess_result is None:
                return None

            if not report_path.exists():
                return None

            try:
                with report_path.open("r", encoding="utf-8") as file:
                    report = json.load(file)
            except (json.JSONDecodeError, OSError):
                return None

            tests = report.get("tests", [])
            if not isinstance(tests, list):
                return None

            return {t["nodeid"]: t for t in tests if isinstance(t, dict) and "nodeid" in t}

    def flaky_tests_post(self, run: Run):
        """
        Rerun the tests that passed normally with network access disabled, and classify any
        of them that fails.
        """
        passed_tests = [
            test for test in run.tests if any(execution.outcome == "passed" for execution in test.executions)
        ]

        blocked_reports = None
        if passed_tests:
            blocked_reports = self._run_with_disabled_socket([test.name for test in passed_tests])

        for test in run.tests:
            baseline_passed = any(execution.outcome == "passed" for execution in test.executions)

            confirmed_flaky = False
            if baseline_passed and blocked_reports is not None:
                blocked_report = blocked_reports.get(test.name)
                if blocked_report is not None:
                    confirmed_flaky = self._test_report_confirmed_flaky(blocked_report)

            result = FlakefighterResult(name=self.__class__.__name__, flaky=confirmed_flaky)
            if result not in test.flakefighter_results:
                test.flakefighter_results.append(result)
