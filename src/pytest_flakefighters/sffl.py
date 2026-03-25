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


class SFFL:  # pylint: disable=R0902
    """
    This class implements Spectrum-based Flaky Fault Localization ranking.
    """

    def __init__(
        self, root: str, metric: str = "ochiai", output_file: str = "sffl.csv", include_test_code: bool = False
    ):
        """
        Go through each test in the test suite and calculate a suspiciousness score for each code statement.
        :param root: The root directory of the project.
        :param metric: The metric to use [tarantula, ochiai, dstar, barinel, op2]. (defaults to ochiai)
        :param output_file: Where to save the suspiciousness results. (defaults to sffl.csv)
        :param include_test_code: Whether to include test code in the suspiciousness ranking. (defaults to False)
        """
        self.root = root
        self.output_file = output_file
        self.metric = getattr(self, metric.lower())
        self.include_test_code = include_test_code

        self.total_flaky = 0
        self.total_stable = 0
        self.flaky = defaultdict(int)
        self.stable = defaultdict(int)

    def tarantula(self, s: tuple[str, int]) -> float:
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

    def ochiai(self, s: tuple[str, int]):
        """
        The formula to calculate the Ochiai suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        return safe_div(self.flaky[s], (sqrt(self.total_flaky * (self.flaky[s] + self.stable[s]))))

    def dstar(self, s: tuple[str, int], exponent: float = 2):
        """
        The formula to calculate the DStar suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        return safe_div(self.flaky[s] ** exponent, (self.stable[s] + (self.total_flaky - self.flaky[s])))

    def barinel(self, s: tuple[str, int]) -> float:
        """
        The formula to calculate the Barinel suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        return 1 - safe_div(self.stable[s], self.stable[s] + self.flaky[s])

    def op2(self, s: tuple[str, int]) -> float:
        """
        The formula to calculate the OP2 suspiciousness score.
        :param s: The current statement (file, line).
        :return: The suspiciousness score of the current statement.
        """
        return self.flaky[s] - safe_div(self.stable[s], self.total_stable + 1)

    def rank(self, tests: list[Test]):
        """
        Calculate the supiciousness score of each code statement and rank them most to least suspicious.
        :param tests: The test suite.
        """
        all_covered_lines = {}
        for test in tests:
            for execution in test.executions:
                for file, lines in execution.coverage.items():
                    if file.startswith(self.root) and (file != test.fspath or self.include_test_code):
                        all_covered_lines[file] = set.union(all_covered_lines.get(file, set()), lines)
            if test.flaky:
                self.total_flaky += 1
                update_covered(self.flaky, total_coverage(self.root, test))
            else:
                self.total_stable += 1
                update_covered(self.stable, total_coverage(self.root, test))

        flat = [(file, line, self.metric((file, line))) for file, lines in all_covered_lines.items() for line in lines]
        pd.DataFrame(flat, columns=["file", "line", "suspiciousness"]).sort_values(
            ["suspiciousness", "line", "file"], ascending=[False, True, True]
        ).reset_index(drop=True).to_csv(self.output_file)
