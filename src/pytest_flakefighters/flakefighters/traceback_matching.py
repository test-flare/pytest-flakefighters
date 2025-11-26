"""
This module implements three FlakeFighters based on failure de-duplication from Alshammari et. al.
[https://arxiv.org/pdf/2401.15788].
"""

import os
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    TestExecution,
)
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter


class TracebackMatching(FlakeFighter):
    """
    Simple text-based matching classifier from Section II.A of [Alshammari et. al.].
    We implement text-based matching on the failure logs for each test. Each failure log is represented by its failure
    exception and stacktrace.
    """

    def __init__(self, run_live: bool, previous_runs: list[Run], root: str = "."):
        super().__init__(run_live)
        self.root = os.path.abspath(root)
        self.previous_runs = previous_runs
        print("TracebackMatching")

    @classmethod
    def from_config(cls, config: dict):
        """
        Factory method to create a new instance from a pytest configuration.
        """
        return TracebackMatching(
            run_live=config.get("run_live", True),
            previous_runs=config["database"].previous_runs,
            root=config.get("root", "."),
        )

    def params(self):
        """
        Convert the key parameters into a dictionary so that the object can be replicated.
        :return A dictionary of the parameters used to create the object.
        """
        return {"root": self.root}

    def _flaky_execution(self, execution, previous_executions) -> bool:
        """
        Classify an execution as flaky if any of its failing executions has a traceback that matches a test previously
        classed as flaky.
        :return: Boolean True if the test is classed as flaky and False otherwise.
        """
        if not execution.exception:
            return False
        current_traceback = [
            (os.path.relpath(e.path, self.root), e.lineno, e.colno, e.statement)
            for e in execution.exception.traceback
            if os.path.commonpath([self.root, e.path]) == self.root
        ]
        return any(e == current_traceback for e in previous_executions)

    def previous_flaky_executions(self, runs: list[Run] = None) -> list:
        """
        Extract the relevant information from previous flaky executions and collapse into a single list.
        :param runs: The runs to consider. Defaults to self.previous_runs.
        :return: List containing the relative path, line number, column number, and code statement of all previous
        test executions.
        """
        if runs is None:
            runs = self.previous_runs
        return [
            [
                (os.path.relpath(elem.path, run.root), elem.lineno, elem.colno, elem.statement)
                for elem in execution.exception.traceback
            ]
            for run in runs
            for test in run.tests
            if test.flaky
            for execution in test.executions
            if execution.exception
        ]

    def flaky_test_live(self, execution: TestExecution):
        """
        Classify executions as flaky if they have the same failure logs as a flaky execution.
        :param execution: Test execution to consider.
        """
        execution.flakefighter_results.append(
            FlakefighterResult(
                name=self.__class__.__name__,
                flaky=self._flaky_execution(
                    execution,
                    self.previous_flaky_executions(),
                ),
            )
        )

    def flaky_tests_post(self, run: Run) -> list[bool | None]:
        """
        Classify failing executions as flaky if any if their executions are flaky.
        :param run: Run object representing the pytest run, with tests accessible through run.tests.
        """
        for test in run.tests:
            for execution in test.executions:
                execution.flakefighter_results.append(
                    FlakefighterResult(
                        name=self.__class__.__name__,
                        flaky=self._flaky_execution(
                            execution, self.previous_flaky_executions(self.previous_runs + [run])
                        ),
                    )
                )


class CosineSimilarity(TracebackMatching):
    """
    TF-IDF cosine similarity matching classifier from Section II.C of [Alshammari et. al.].
    Test executions are classified as flaky if the stack trace is sufficiently similar to a previous flaky execution.
    """

    def __init__(self, run_live: bool, previous_runs: list[Run], root: str = ".", threshold: float = 1):
        super().__init__(run_live, previous_runs, root)
        self.root = os.path.abspath(root)
        self.previous_runs = previous_runs
        self.threshold = threshold

    @classmethod
    def from_config(cls, config: dict):
        """
        Factory method to create a new instance from a pytest configuration.
        """
        return CosineSimilarity(
            run_live=config.get("run_live", True),
            previous_runs=config["database"].previous_runs,
            root=config.get("root", "."),
        )

    def _tf_idf_matrix(self, executions):
        corpus = [
            re.sub(r"[^\w\s]", " ", "\n".join([" ".join(map(str, tuple)) for tuple in execution]))
            for execution in executions
        ]
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(corpus)

        feature_names = vectorizer.get_feature_names_out()
        return pd.DataFrame(tfidf_matrix.toarray(), columns=feature_names)

    def _flaky_execution(self, execution, previous_executions) -> bool:
        """
        Classify an execution as flaky if the test execution is sufficiently cosine-similar to any of the previous
        executions.
        :return: Boolean True if the test is classed as flaky and False otherwise.
        """
        if not execution.exception or not previous_executions:
            return False

        execution = [
            (os.path.relpath(elem.path, self.root), elem.lineno, elem.colno, elem.statement)
            for elem in execution.exception.traceback
        ]

        tf_idf_matrix = self._tf_idf_matrix([execution] + previous_executions)

        similarity = cosine_similarity(tf_idf_matrix.iloc[0].values.reshape(1, -1), tf_idf_matrix.iloc[1:].values)
        return (similarity >= self.threshold).any()
