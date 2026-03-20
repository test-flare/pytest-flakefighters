"""
This module implements Spectrum-based Flaky Fault Localization [10.1109/AST58925.2023.00017] to calculate the
suspiciousness score of code statements based on how likely they are to be the cause of test flakiness.
"""

from collections import defaultdict
from math import sqrt

import pandas as pd

from pytest_flakefighters.database_management import Test


def total_coverage(root: str, test: Test) -> dict[str, set[int]]:
    """
    Merge lines covered by all test executions into a single dictionary.
    :param root: The root directory of the repo.
    :param test: The test to be processed.
    :returns: Dictionary mapping filename to lines covered.
    """
    coverage = {}
    reduce = set.intersection if test.flaky else set.union
    for execution in test.executions:
        for file, lines in execution.coverage.items():
            if file.startswith(root):
                coverage[file] = coverage.get(file, []) + [set(lines)]
    return {file: reduce(*lines) for file, lines in coverage.items()}


def update_covered(covered: dict[tuple[str, int], int], coverage: dict[str, list[int]]):
    """
    Update the counts of lines covered by flaky/stable tests.
    :param covered: Dictionary mapping (filename, line) to number of tests covered.
    :param coverage: Test coverage to update.
    """
    for file, lines in coverage.items():
        for line in lines:
            covered[(file, line)] = covered.get((file, line), 0) + 1


def safe_div(x: float, y: float) -> float:
    """Save division by zero as specified in [10.1109/TR.2013.2285319].

    :param x: numerator
    :param y: denominator
    :returns: 0 if x=0 and y=0, else ∞ if y=0, else x/y.

    """
    if y == 0:
        if x > 0:
            return float("inf")
        if x < 0:
            return -float("inf")
        return 0
    return x / y


class SFFL:
    """
    This class implements Spectrum-based Flaky Fault Localization ranking.
    """

    def __init__(self, root: str, tests: list[Test]):
        """
        Go through each test in the test suite and calculate a suspiciousness score for each code statement.
        :param tests: The test suite.
        """
        total_flaky = 0
        total_stable = 0
        flaky = defaultdict(int)
        stable = defaultdict(int)
        all_covered_lines = {}
        for test in tests:
            for execution in test.executions:
                for file, lines in execution.coverage.items():
                    if file.startswith(root) and file != test.fspath:
                        all_covered_lines[file] = set.union(all_covered_lines.get(file, set()), lines)
            if test.flaky:
                total_flaky += 1
                update_covered(flaky, total_coverage(root, test))
            else:
                total_stable += 1
                update_covered(stable, total_coverage(root, test))
        self.total_flaky = total_flaky
        self.total_stable = total_stable
        self.flaky = flaky
        self.stable = stable
        self.all_covered_lines = all_covered_lines

    def _tarantula(self, s: tuple[str, int]) -> float:
        """
        The formula to calculate the Tarantula suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        result = safe_div(
            safe_div(self.flaky[s], self.total_flaky),
            (safe_div(self.flaky[s], self.total_flaky) + safe_div(self.stable[s], self.total_stable)),
        )
        return result

    def _ochiai(self, s: tuple[str, int]):
        """
        The formula to calculate the Ochiai suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        return safe_div(self.flaky[s], (sqrt(self.total_flaky * (self.flaky[s] + self.stable[s]))))

    def _dstar(self, s: tuple[str, int], exponent: float = 2):
        """
        The formula to calculate the DStar suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        return safe_div(self.flaky[s] ** exponent, (self.stable[s] + (self.total_flaky - self.flaky[s])))

    def _barinel(self, s: tuple[str, int]) -> float:
        """
        The formula to calculate the Barinel suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        return 1 - safe_div(self.stable[s], self.stable[s] + self.flaky[s])

    def _op2(self, s: tuple[str, int]) -> float:
        """
        The formula to calculate the OP2 suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        return self.flaky[s] - safe_div(self.stable[s], self.total_stable + 1)

    def _rank(self, metric):
        flat = [(file, line, metric((file, line))) for file, lines in self.all_covered_lines.items() for line in lines]
        return (
            pd.DataFrame(flat, columns=["file", "line", "suspiciousness"])
            .sort_values(["suspiciousness", "line", "file"], ascending=[False, True, True])
            .reset_index(drop=True)
        )

    def tarantula(self):
        """
        Rank the covered statements using the Tarantula metric.
        """
        return self._rank(self._tarantula)

    def ochiai(self):
        """
        Rank the covered statements using the Ochiai metric.
        """
        return self._rank(self._ochiai)

    def dstar(self):
        """
        Rank the covered statements using the DStar metric.
        """
        return self._rank(self._dstar)

    def barinel(self):
        """
        Rank the covered statements using the Barinel metric.
        """
        return self._rank(self._barinel)

    def op2(self):
        """
        Rank the covered statements using the OP2 metric.
        """
        return self._rank(self._op2)
