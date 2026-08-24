"""
Detect order-dependent flaky tests by perturbing test execution order.
"""

import json
import os
import random
import subprocess
import sys
import tempfile
from collections import defaultdict
from typing import Any, Optional

from pytest_flakefighters.database_management import (
    Database,
    FlakefighterResult,
    OrderDependencyExecution,
    Run,
    TestExecution,
)
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter

class OrderDependency(FlakeFighter):
    """
    Detect tests whose outcome changes when execution order changes.

    Modes:
        random:
            One shuffled run is performed by default.
            --order-runs controls how many fresh shuffled runs are performed.

        reverse:
            Execute the test suite once in reverse order.
            --order-runs does not apply to reverse mode.
    """

    RANDOM = "random"
    REVERSE = "reverse"

    def __init__(
        self,
        database: Database,
        mode: str = RANDOM,
        order_runs: int = 1,
        extra_pytest_args: Optional[list[str]] = None,
    ):
        super().__init__(run_live=False)

        if mode not in (self.RANDOM, self.REVERSE):
            raise ValueError(f"Unsupported order-dependency mode: {mode}")

        self.database = database
        self.mode = mode
        self.order_runs = max(1, order_runs)
        self.extra_pytest_args = extra_pytest_args or []

    @classmethod
    def from_config(cls, config: dict):
        """
        Create the classifier from the pytest/FlakeFighters configuration.
        """

        return cls(
            database=config["database"],
            mode=config.get("order_mode") or cls.RANDOM,
            order_runs=int(config.get("order_runs") or 1),
        )

    def params(self) -> dict:
        """
        Return configuration used by this FlakeFighter.
        """

        return {"mode": self.mode, "order_runs": self.order_runs}

    def flaky_test_live(self, execution: TestExecution):
        """
        OrderDependency does not support live classification.
        """

    def flaky_tests_post(self, run: Run):
        """
        Run the order-dependency experiment and classify tests.
        """
        baseline = self._collect_baseline(run)

        if not baseline:
            return

        outcomes = defaultdict(set)

        for nodeid, outcome in baseline.items():
            outcomes[nodeid].add(outcome)

        if self.mode == self.RANDOM:
            historical = self._load_historical_outcomes()

            for nodeid, historical_outcomes in historical.items():
                outcomes[nodeid].update(historical_outcomes)

        if self.mode == self.REVERSE:
            number_of_runs = 1
            next_seed = None
        else:
            number_of_runs = self.order_runs
            next_seed = self._next_seed()

        for run_number in range(number_of_runs):
            seed = None

            if self.mode == self.RANDOM:
                seed = next_seed + run_number

            ordered_nodeids = self._make_order(list(baseline.keys()), seed)

            report = self._run_ordered_tests(ordered_nodeids=ordered_nodeids, cwd=run.root)

            if report is None:
                continue

            perturbed_outcomes = self._extract_outcomes(report)

            if not perturbed_outcomes:
                continue

            self._store_order_execution(
                run=run,
                mode=self.mode,
                seed=seed,
                ordered_nodeids=ordered_nodeids,
                outcomes=perturbed_outcomes,
            )

            for nodeid, outcome in perturbed_outcomes.items():
                outcomes[nodeid].add(outcome)

        self._classify(run, outcomes)

    @staticmethod
    def _collect_baseline(run: Run) -> dict[str, str]:
        """
        Collect the current normal PASS/FAIL outcome for each test.
        """

        baseline = {}

        for test in run.tests:
            usable_outcomes = [
                execution.outcome
                for execution in test.executions
                if execution.outcome in ("passed", "failed")
            ]

            if not usable_outcomes:
                continue

            baseline[test.name] = usable_outcomes[-1]

        return baseline

    def _make_order(self, nodeids: list[str], seed: Optional[int]) -> list[str]:
        """
        Produce the requested perturbed execution order.
        """

        ordered = nodeids.copy()

        if self.mode == self.REVERSE:
            ordered.reverse()
            return ordered

        rng = random.Random(seed)
        rng.shuffle(ordered)

        return ordered

    def _next_seed(self) -> int:
        """
        Return the next sequential seed for random mode.
        """

        seeds = {
            execution.seed
            for previous_run in self.database.previous_runs
            for execution in previous_run.order_dependency_executions
            if (execution.mode == self.RANDOM and execution.seed is not None)
        }

        if not seeds:
            return 0

        return max(seeds) + 1

    def _run_ordered_tests(self, ordered_nodeids: list[str], cwd: str) -> Optional[dict[str, Any]]:
        """
        Execute the supplied order in a fresh pytest subprocess.
        """

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as report_file:
            report_path = report_file.name

        command = [
            sys.executable,
            "-m",
            "pytest",
            *ordered_nodeids,
            "-p",
            "no:flakefighters",
            "--json-report",
            f"--json-report-file={report_path}",
            "-q",
            *self.extra_pytest_args,
        ]

        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=cwd,
                env=self._subprocess_env(),
                check=False,
            )

            if not os.path.exists(report_path):
                return None

            with open(report_path, encoding="utf-8") as report_fd:
                return json.load(report_fd)

        except (OSError, json.JSONDecodeError):
            return None

        finally:
            if os.path.exists(report_path):
                os.remove(report_path)

    @staticmethod
    def _subprocess_env() -> dict[str, str]:
        """
        Build a clean environment for the perturbation subprocess.
        """

        env = os.environ.copy()

        env.pop("PYTEST_ADDOPTS", None)
        env.pop("COVERAGE_FILE", None)

        return env

    @staticmethod
    def _extract_outcomes(report: dict[str, Any]) -> dict[str, str]:
        """
        Extract only PASS/FAIL outcomes from the pytest JSON report.
        """

        outcomes = {}

        for test_report in report.get("tests", []):
            nodeid = test_report.get("nodeid")
            outcome = test_report.get("outcome")

            if nodeid is None:
                continue

            if outcome not in ("passed", "failed"):
                continue

            outcomes[nodeid] = outcome

        return outcomes

    def _load_historical_outcomes(self) -> dict[str, set[str]]:
        """
        Load historical random-order outcomes.
        """

        outcomes = defaultdict(set)

        for previous_run in self.database.previous_runs:
            for execution in previous_run.order_dependency_executions:
                if execution.mode != self.RANDOM:
                    continue

                if execution.outcome not in ("passed", "failed"):
                    continue

                outcomes[execution.test.name].add(execution.outcome)

        return outcomes

    @staticmethod
    def _store_order_execution(
        run: Run,
        mode: str,
        seed: Optional[int],
        ordered_nodeids: list[str],
        outcomes: dict[str, str],
    ):
        """
        Store one complete perturbation execution.
        """

        tests_by_name = {test.name: test for test in run.tests}

        for position, nodeid in enumerate(ordered_nodeids):
            outcome = outcomes.get(nodeid)

            if outcome not in ("passed", "failed"):
                continue

            test = tests_by_name.get(nodeid)

            if test is None:
                continue

            execution = OrderDependencyExecution(
                mode=mode, seed=seed, position=position, outcome=outcome
            )

            run.order_dependency_executions.append(execution)
            test.order_dependency_executions.append(execution)

    @staticmethod
    def _classify(run: Run, outcomes: dict[str, set[str]]):
        """
        A test is classified as order-dependent whenever both a passing
        and failing outcome are observed in the relevant evidence.
        """

        for test in run.tests:
            test_outcomes = outcomes.get(test.name)

            if not test_outcomes:
                continue

            order_dependent = "passed" in test_outcomes and "failed" in test_outcomes

            result = FlakefighterResult(name="OrderDependency", flaky=order_dependent)

            if result not in test.flakefighter_results:
                test.flakefighter_results.append(result)
