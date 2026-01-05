"""
This module implements the DeFlaker FlakeFighter.
"""

import os

import git
from unidiff import PatchSet

from pytest_flakefighters.database_management import (
    FlakefighterResult,
    Run,
    TestExecution,
)
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter


class DeFlaker(FlakeFighter):
    """
    A python equivalent of the DeFlaker algorithm from Bell et al. 2019 [10.1145/3180155.3180164].
    Given the subtle differences between JUnit and pytest, this is not intended to be an exact port, but it follows
    the same general methodology of checking whether covered code has been changed between commits.

    :ivar root: The root directory of the Git repository.
    :ivar source_commit: The source (older) commit hash. Defaults to HEAD^ (the previous commit to target).
    :ivar target_commit: The target (newer) commit hash. Defaults to HEAD (the most recent commit).
    """

    def __init__(self, run_live: bool, root: str = ".", source_commit: str = None, target_commit: str = None):
        super().__init__(run_live)

        self.repo_root = git.Repo(root)
        if target_commit is None and not self.repo_root.is_dirty():
            # No uncommitted changes, so use most recent commit
            self.target_commit = self.repo_root.commit().hexsha
        else:
            self.target_commit = target_commit
        if source_commit is None:
            if self.target_commit is None:
                # If uncommitted changes, use most recent commit as source
                self.source_commit = self.repo_root.commit().hexsha
            else:
                # If no uncommitted changes, use previous commit as source
                parents = [
                    commit.hexsha
                    for commit in self.repo_root.commit(source_commit).iter_parents()
                    if commit.hexsha != self.target_commit
                ]
                self.source_commit = parents[0]
        else:
            self.source_commit = source_commit

        patches = PatchSet(self.repo_root.git.diff(self.source_commit, self.target_commit, "-U0", "--no-prefix"))
        self.lines_changed = {}
        for patch in patches:
            if patch.target_file == patch.source_file:
                abspath = os.path.join(self.repo_root.working_dir, patch.source_file)
                self.lines_changed[abspath] = []
                for hunk in patch:
                    # Add each line in the hunk to lines_changed
                    self.lines_changed[abspath] += list(
                        range(hunk.target_start, hunk.target_start + hunk.target_length)
                    )

    @classmethod
    def from_config(cls, config: dict):
        """
        Factory method to create a new instance from a pytest configuration.
        """
        return DeFlaker(
            run_live=config.get("run_live", True),
            root=config.get("root", "."),
            source_commit=config.get("source_commit"),
            target_commit=config.get("target_commit"),
        )

    def params(self):
        """
        Convert the key parameters into a dictionary so that the object can be replicated.
        :return A dictionary of the parameters used to create the object.
        """
        return {"root": self.repo_root, "source_commit": self.source_commit, "target_commit": self.target_commit}

    def line_modified_by_target_commit(self, file_path: str, line_number: int) -> bool:
        """
        Returns true if the given line in the file has been modified by the present commit.

        :param file_path: The file to check.
        :param line_number: The line number to check.
        """
        return line_number in self.lines_changed.get(file_path, [])

    def _flaky_execution(self, execution):
        """
        Classify an execution as flaky or not.
        :return: Boolean True of the test is classed as flaky and False otherwise.
        """
        return execution.outcome != "passed" and not any(
            self.line_modified_by_target_commit(file_path, line_number)
            for file_path in execution.coverage
            for line_number in execution.coverage[file_path]
            if file_path in self.lines_changed
        )

    def flaky_test_live(self, execution: TestExecution):
        """
        Classify a failing test as flaky if it does not cover any code which has been changed between the source and
        target commits.
        :param execution: The test execution to classify.
        """
        execution.flakefighter_results.append(
            FlakefighterResult(name=self.__class__.__name__, flaky=self._flaky_execution(execution))
        )

    def flaky_tests_post(self, run: Run) -> list[bool | None]:
        """
        Classify failing tests as flaky if any of their executions are flaky.
        :param run: Run object representing the pytest run, with tests accessible through run.tests.
        """
        for test in run.tests:
            test.flakefighter_results.append(
                FlakefighterResult(
                    name=self.__class__.__name__,
                    flaky=any(self._flaky_execution(execution) for execution in test.executions),
                )
            )
