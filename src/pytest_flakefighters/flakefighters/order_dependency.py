"""
Order-dependency FlakeFighter.

This classifier detects tests whose outcomes change when the execution
order of the collected test suite is perturbed.

The normal pytest execution performed by pytest-flakefighters is used as
the baseline.

Supported perturbation modes:

    random:
        Globally shuffle all collected tests.

    reverse:
        Reverse the complete collected test order.

    both:
        Perform the configured number of random-order runs and one
        reverse-order run.

Classification rule:

    baseline PASS + perturbed FAIL -> order-sensitive (flaky=True)

    baseline FAIL + perturbed PASS -> order-sensitive (flaky=True)

All other outcome combinations are classified as flaky=False.

No external pytest ordering plugin is required.
"""

import json
import os
import random
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


class OrderDependency(FlakeFighter):
    """
    Detect order-sensitive tests by perturbing the complete collected suite.

    This FlakeFighter runs in post-processing mode because it requires the
    complete set of tests from the baseline pytest execution.

    Random mode globally shuffles the collection.

    Reverse mode reverses the collection.

    A test is considered order-sensitive if its PASS/FAIL outcome changes
    between the normal baseline execution and any perturbed execution.
    """

    DEFAULT_MODE = "random"
    DEFAULT_RUNS = 1

    VALID_MODES = {
        "random",
        "reverse",
        "both",
    }

    def __init__(
        self,
        mode: str = DEFAULT_MODE,
        runs: int = DEFAULT_RUNS,
        extra_pytest_args: list[str] | None = None,
    ):
        # Order dependency requires the complete test suite, so this fighter
        # runs only in post-processing mode.
        super().__init__(False)

        if mode not in self.VALID_MODES:
            raise ValueError(
                f"Invalid order-dependency mode '{mode}'. "
                f"Expected one of: {', '.join(sorted(self.VALID_MODES))}"
            )

        if runs <= 0:
            raise ValueError(
                "order dependency runs must be greater than 0"
            )

        self.mode = mode
        self.runs = runs
        self.extra_pytest_args = extra_pytest_args or []

    @classmethod
    def from_config(cls, config: dict):
        """
        Factory method used by pytest-flakefighters.
        """
        return cls(
            mode=config.get(
                "order_dependency_mode",
                cls.DEFAULT_MODE,
            ),
            runs=config.get(
                "order_dependency_runs",
                cls.DEFAULT_RUNS,
            ),
            extra_pytest_args=config.get(
                "order_dependency_extra_pytest_args",
                [],
            ),
        )

    def params(self):
        """
        Return parameters needed to reproduce this classifier instance.
        """
        return {
            "mode": self.mode,
            "runs": self.runs,
            "extra_pytest_args": self.extra_pytest_args,
        }

    def flaky_test_live(
        self,
        execution: TestExecution,
    ):
        """
        Live classification is not supported.
        """
        raise NotImplementedError(
            "Order dependency cannot be measured live"
        )

    def _normalise_outcome(
        self,
        outcome: str | None,
    ) -> str | None:
        """
        Normalize pytest outcomes for comparison.

        Errors are treated as failures.
        """
        if outcome is None:
            return None

        outcome = str(outcome).lower()

        if outcome == "passed":
            return "passed"

        if outcome in {
            "failed",
            "error",
        }:
            return "failed"

        return outcome

    def _outcome_changed(
        self,
        baseline: str | None,
        perturbed: str | None,
    ) -> bool:
        """
        Return True only when PASS/FAIL outcome changes.

        Examples:

            PASS -> FAIL = True
            FAIL -> PASS = True

            PASS -> PASS = False
            FAIL -> FAIL = False
            PASS -> SKIPPED = False
            SKIPPED -> PASS = False
        """
        baseline = self._normalise_outcome(
            baseline
        )

        perturbed = self._normalise_outcome(
            perturbed
        )

        return (
            baseline in {"passed", "failed"}
            and perturbed in {"passed", "failed"}
            and baseline != perturbed
        )

    def _baseline_executions(
        self,
        run: Run,
    ) -> dict[str, TestExecution]:
        """
        Get the original baseline execution for each test.

        The first execution is used because it represents the test's
        execution in the original suite order.
        """
        baseline = {}

        for test in run.tests:
            if not test.executions:
                continue

            baseline[test.name] = test.executions[0]

        return baseline

    def _nodeids(
        self,
        run: Run,
    ) -> list[str]:
        """
        Return test node IDs in the baseline collection order.
        """
        return [
            test.name
            for test in run.tests
            if test.executions
        ]

    def _write_ordering_plugin(
        self,
        directory: Path,
    ) -> Path:
        """
        Create a temporary pytest plugin that perturbs collection order.

        Random mode:
            random.shuffle(items)

        Reverse mode:
            items.reverse()

        The target project itself is not modified.
        """
        plugin_path = (
            directory
            / "ff_order_perturbation.py"
        )

        plugin_path.write_text(
            '''
import os
import random

import pytest


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    mode = os.environ.get(
        "FF_ORDER_MODE",
        "random",
    )

    if mode == "random":
        random.shuffle(items)

    elif mode == "reverse":
        items.reverse()
''',
            encoding="utf-8",
        )

        return plugin_path

    def _find_test_outcomes(
        self,
        report: dict[str, Any],
    ) -> dict[str, str]:
        """
        Extract nodeid -> outcome from pytest-json-report output.
        """
        outcomes = {}

        tests = report.get(
            "tests",
            [],
        )

        if not isinstance(tests, list):
            return outcomes

        for test_report in tests:
            if not isinstance(
                test_report,
                dict,
            ):
                continue

            nodeid = test_report.get(
                "nodeid"
            )

            outcome = test_report.get(
                "outcome"
            )

            if (
                nodeid is None
                or outcome is None
            ):
                continue

            outcomes[str(nodeid)] = (
                self._normalise_outcome(
                    str(outcome)
                )
            )

        return outcomes

    def _run_perturbed_suite(
        self,
        nodeids: list[str],
        mode: str,
    ) -> dict[str, str]:
        """
        Run the complete collected suite in a perturbed order.

        Returns:
            Dictionary mapping test node IDs to outcomes.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(
                tmpdir
            )

            self._write_ordering_plugin(
                tmp_path
            )

            report_path = (
                tmp_path
                / "order_dependency_report.json"
            )

            command = [
                sys.executable,
                "-m",
                "pytest",

                # Run exactly the tests collected in the baseline run.
                *nodeids,

                # Prevent recursive FlakeFighters execution.
                "-p",
                "no:pytest_flakefighters",

                # Load temporary ordering plugin.
                "-p",
                "ff_order_perturbation",

                "--json-report",
                f"--json-report-file={report_path}",

                "-q",
            ]

            command.extend(
                self.extra_pytest_args
            )

            environment = (
                os.environ.copy()
            )

            environment[
                "FF_ORDER_MODE"
            ] = mode

            old_pythonpath = (
                environment.get(
                    "PYTHONPATH",
                    "",
                )
            )

            if old_pythonpath:
                environment[
                    "PYTHONPATH"
                ] = (
                    f"{tmp_path}"
                    f"{os.pathsep}"
                    f"{old_pythonpath}"
                )
            else:
                environment[
                    "PYTHONPATH"
                ] = str(
                    tmp_path
                )

            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
            )

            if not report_path.exists():
                print(
                    (
                        "\n[OrderDependency] "
                        f"No JSON report produced "
                        f"for {mode} run."
                    ),
                    file=sys.stderr,
                )

                if completed.stderr:
                    print(
                        completed.stderr,
                        file=sys.stderr,
                    )

                return {}

            try:
                with report_path.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    report = json.load(
                        file
                    )

            except (
                json.JSONDecodeError,
                OSError,
            ):
                print(
                    (
                        "\n[OrderDependency] "
                        f"Unable to read JSON "
                        f"report for {mode} run."
                    ),
                    file=sys.stderr,
                )

                return {}

            return self._find_test_outcomes(
                report
            )

    def _random_runs(
        self,
        nodeids: list[str],
    ) -> list[dict[str, str]]:
        """
        Execute the configured number of random-order runs.
        """
        results = []

        for run_number in range(
            self.runs
        ):
            print(
                (
                    "\n[OrderDependency] "
                    f"Random-order run "
                    f"{run_number + 1}/{self.runs}"
                ),
                file=sys.stderr,
            )

            outcomes = (
                self._run_perturbed_suite(
                    nodeids=nodeids,
                    mode="random",
                )
            )

            results.append(
                outcomes
            )

        return results

    def _reverse_run(
        self,
        nodeids: list[str],
    ) -> dict[str, str]:
        """
        Execute one reverse-order run.

        Reverse mode is deterministic, so repeating it would produce
        the same order each time.
        """
        print(
            "\n[OrderDependency] "
            "Reverse-order run",
            file=sys.stderr,
        )

        return self._run_perturbed_suite(
            nodeids=nodeids,
            mode="reverse",
        )

    def flaky_tests_post(
        self,
        run: Run,
    ):
        """
        Perturb execution order and compare outcomes with the baseline.

        Default:
            random mode
            one random-order run

        Random:
            baseline vs N random-order runs

        Reverse:
            baseline vs one reverse-order run

        Both:
            baseline vs N random-order runs
            plus one reverse-order run
        """
        baseline = (
            self._baseline_executions(
                run
            )
        )

        nodeids = self._nodeids(
            run
        )

        if not nodeids:
            return

        perturbed_runs: list[
            dict[str, str]
        ] = []

        if self.mode in {
            "random",
            "both",
        }:
            perturbed_runs.extend(
                self._random_runs(
                    nodeids
                )
            )

        if self.mode in {
            "reverse",
            "both",
        }:
            perturbed_runs.append(
                self._reverse_run(
                    nodeids
                )
            )

        for (
            nodeid,
            execution,
        ) in baseline.items():

            baseline_outcome = (
                execution.outcome
            )

            order_sensitive = False

            for outcomes in perturbed_runs:
                perturbed_outcome = (
                    outcomes.get(
                        nodeid
                    )
                )

                if self._outcome_changed(
                    baseline_outcome,
                    perturbed_outcome,
                ):
                    order_sensitive = True
                    break

            execution.flakefighter_results.append(
                FlakefighterResult(
                    name=self.__class__.__name__,
                    flaky=order_sensitive,
                )
            )