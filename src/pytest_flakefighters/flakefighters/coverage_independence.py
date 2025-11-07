"""
This module implements the CoverageIndependence FlakeFighter.
"""

import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    TestExecution,
)
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter


class CoverageIndependence(FlakeFighter):
    """
    Classify tests as flaky if they fail independently of passing test cases that exercise overlapping code.

    :ivar threshold: The minimum distance to consider as "similar", expressed as a proportion 0 <= threshold < 1 where 0
    represents no difference and 1 represents complete difference.
    :ivar metric: From `scipy.spatial.distance`: [‘braycurtis’, ‘canberra’, ‘chebyshev’, ‘correlation’, ‘dice’,
    ‘hamming’, ‘jaccard’, ‘kulsinski’, ‘mahalanobis’, ‘minkowski’, ‘rogerstanimoto’, ‘russellrao’, ‘seuclidean’,
    ‘sokalmichener’, ‘sokalsneath’, ‘sqeuclidean’, ‘yule’].
    """

    def __init__(self, threshold: float = 0, metric: str = "jaccard"):
        super().__init__(False)
        self.threshold = threshold
        self.metric = metric

    def flaky_test_live(self, execution: TestExecution):
        """
        NOT SUPPORTED.
        Detect whether a given test execution is flaky and append the result to its `flakefighter_results` attribute.
        :param execution: The test execution to classify.
        """
        raise NotImplementedError("Coverage independence cannot be measured live")

    def flaky_tests_post(self, run: Run):
        """
        Go through each test in the test suite and append the result to its `flakefighter_results` attribute.
        :param run: Run object representing the pytest run, with tests accessible through run.tests.
        """
        coverage = []
        # Enumerating tests and executions since they won't have IDs if they are not yet in the database
        for test in run.tests:
            for execution in test.executions:
                coverage.append(
                    {"test": test, "execution": execution}
                    | {f"{file}:{line}": True for file in execution.coverage for line in execution.coverage[file]}
                )

        # Can't compute the pairwise distance of a single execution
        if len(coverage) < 2:
            return

        coverage = pd.DataFrame(coverage)
        coverage[coverage.columns.drop(["test", "execution"])] = coverage[
            coverage.columns.drop(["test", "execution"])
        ].fillna(False)
        # Calculate the distance between each pair of test executions
        raw_coverage = coverage.drop(["test", "execution"], axis=1).to_numpy()
        distances = pdist(raw_coverage, metric=self.metric)
        # Assign each test execution to a cluster
        coverage["cluster"] = fcluster(linkage(distances, method="single"), t=self.threshold, criterion="distance")

        coverage.to_csv("/tmp/coverage.csv")

        for _, group in coverage.groupby("cluster"):
            for test in group["test"]:
                result = FlakefighterResult(
                    name=self.__class__.__name__,
                    flaky=len(set(map(lambda x: x.outcome, group["execution"]))) > 1,
                )
                if result not in test.flakefighter_results:
                    test.flakefighter_results.append(result)
