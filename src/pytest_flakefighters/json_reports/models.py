"""Pydantic models describing the FlakeFighters JSON output."""

# pylint: disable=too-few-public-methods

from datetime import datetime
from typing import Any, Dict, List, Optional

import git
from pydantic import BaseModel, ConfigDict, field_serializer

class FlakefighterResultModel(BaseModel):
    """A result produced by a FlakeFighter."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    test_execution_id: Optional[int]
    test_id: Optional[int]
    name: str
    flaky: bool

class ActiveFlakeFighterModel(BaseModel):
    """A FlakeFighter enabled for a run."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    name: str
    params: Dict[str, Any]

    @field_serializer("params", when_used="json")
    def serialize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python-specific parameter values to JSON representations."""
        return {key: value.working_tree_dir if isinstance(value, git.Repo) else value for key, value in params.items()}

class TracebackEntryModel(BaseModel):
    """An entry in a test exception traceback."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    exception_id: int
    path: str
    lineno: int
    colno: Optional[int]
    statement: str
    source: str

class TestExceptionModel(BaseModel):
    """An exception raised during a test execution."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: int
    name: str
    traceback: List[TracebackEntryModel]

class TestExecutionModel(BaseModel):
    """A single execution of a test."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    test_id: int
    outcome: str
    stdout: Optional[str]
    stderr: Optional[str]
    report: Optional[str]
    start_time: datetime
    end_time: datetime
    coverage: Dict

    flakefighter_results: List[FlakefighterResultModel]
    exception: Optional[TestExceptionModel]

class TestModel(BaseModel):
    """A test belonging to a run."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    fspath: str
    line_no: int
    name: str
    skipped: bool

    flakefighter_results: List[FlakefighterResultModel]
    executions: List[TestExecutionModel]

class RunModel(BaseModel):
    """A pytest-flakefighters run."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: datetime
    created_at: datetime
    root: str
    commit_sha: Optional[str]

    active_flakefighters: List[ActiveFlakeFighterModel]
    tests: List[TestModel]

class FlakefightersReport(BaseModel):
    """Complete FlakeFighters JSON report."""

    runs: List[RunModel]
