"""
This module implements the FlakeFighter abstract class and our supported flake fighter classes.
Each of these is a microservice which takes a failed test and classifies that failure as either genuine or flaky.
The failure detectors can be configured to either run "live" after each test, or as a postprocessing step after the test
suite has been run.
If running live, detectors are run at the end of pytest_runtest_makereport.
If running as a postprocessing step, detectors are run at the start of pytest_sessionfinish.
"""

import os
from abc import ABC, abstractmethod

import git
import pytest
from unidiff import PatchSet


class FlakeFighter(ABC):  # pylint: disable=R0903
    """
    Abstract base class for a FlakeFighter
    :ivar run_live: Run detection "live" after each test. Otherwise run as a postprocessing step after the test suite.
    """

    def __init__(self, run_live: bool):
        self.run_live = run_live

    @abstractmethod
    def flaky_failure(self, item: pytest.Item, call: pytest.CallInfo[None]) -> bool:
        """
        Detect whether a failed test is flaky.
        :param item: The item.
        :param call: The :class:`~pytest.CallInfo` for the phase.
        """


class DeFlaker(FlakeFighter):
    """
    A python equivalent of the DeFlaker algorithm from Bell et al. 2019 [10.1145/3180155.3180164].
    Given the subtle differences between JUnit and pytest, this is not intended to be an exact port, but it follows
    the same general methodology of checking whether covered code has been changed between commits.

    :ivar repo_root: The root directory of the Git repository.
    :ivar source_commit: The source (older) commit hash. Defaults to HEAD^ (the previous commit to target).
    :ivar target_commit: The target (newer) commit hash. Defaults to HEAD (the most recent commit).
    """

    def __init__(self, run_live: bool, repo_root: str, source_commit: str, target_commit: str):
        super().__init__(run_live)

        self.repo = git.Repo(repo_root if repo_root is not None else ".")
        if target_commit is None and not self.repo.is_dirty():
            # No uncommitted changes, so use most recent commit
            self.target_commit = self.repo.commit().hexsha
        else:
            self.target_commit = target_commit
        if source_commit is None:
            if self.target_commit is None:
                # If uncommitted changes, use most recent commit as source
                self.source_commit = self.repo.commit().hexsha
            else:
                # If no uncommitted changes, use previous commit as source
                parents = [
                    commit.hexsha
                    for commit in self.repo.commit(source_commit).iter_parents()
                    if commit.hexsha != self.target_commit
                ]
                self.source_commit = parents[0]
        else:
            self.source_commit = source_commit

        patches = PatchSet(self.repo.git.diff(self.source_commit, self.target_commit, "-U0", "--no-prefix"))
        self.lines_changed = {}
        for patch in patches:
            if patch.target_file == patch.source_file:
                abspath = os.path.join(self.repo.working_dir, patch.source_file)
                self.lines_changed[abspath] = []
                for hunk in patch:
                    # Add each line in the hunk to lines_changed
                    self.lines_changed[abspath] += list(
                        range(hunk.target_start, hunk.target_start + hunk.target_length + 1)
                    )

    def flaky_failure(self, item: pytest.Item, call: pytest.CallInfo[None]) -> bool:
        """
        Detect whether a failed test is flaky based on whether any of the covered code has changed.
        :param item: The item.
        :param call: The :class:`~pytest.CallInfo` for the phase.
        """
        line_coverage = dict(item.user_properties).get("line_coverage", {})
        return not any(
            self.line_modified_by_latest_commit(file_path, line_number)
            for file_path in line_coverage.measured_files()
            for line_number in line_coverage.lines(file_path)
            if file_path in self.lines_changed
        )

    def line_modified_by_latest_commit(self, file_path: str, line_number: int) -> bool:
        """
        Returns true if the given line in the file has been modified by the present commit.

        :param file_path: The file to check.
        :param line_number: The line number to check.
        """
        if line_number in self.lines_changed[file_path]:
            return self.lines_changed[file_path][line_number]
        return True
