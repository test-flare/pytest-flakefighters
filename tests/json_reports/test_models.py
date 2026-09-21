"""Tests for the FlakeFighters JSON Pydantic models."""

from datetime import datetime

import git

from pytest_flakefighters.json_reports.models import (
    ActiveFlakeFighterModel,
    FlakefightersReport,
    RunModel,
)


def test_run_model_from_attributes():
    """Test conversion from object attributes to nested Pydantic models."""

    class Test:
        id = 1
        run_id = 1
        fspath = "tests/test_example.py"
        line_no = 10
        name = "test_example"
        skipped = False
        flakefighter_results = []
        executions = []

    class Run:
        id = 1
        start_time = datetime(2026, 9, 21, 10, 0)
        created_at = datetime(2026, 9, 21, 10, 1)
        root = "/project"
        commit_sha = "abc123"
        active_flakefighters = []
        tests = [Test()]

    model = RunModel.model_validate(Run())

    assert model.root == "/project"
    assert model.commit_sha == "abc123"
    assert model.tests[0].name == "test_example"


def test_active_flakefighter_serializes_git_repo(tmp_path):
    """Test conversion of git.Repo parameters to JSON-compatible paths."""

    repo = git.Repo.init(tmp_path)

    model = ActiveFlakeFighterModel(
        id=1,
        run_id=1,
        name="DiffCov",
        params={"root": repo},
    )

    data = model.model_dump(mode="json")

    assert data["params"]["root"] == repo.working_tree_dir


def test_flakefighters_report_schema():
    """Test generation of the FlakeFighters JSON Schema."""

    schema = FlakefightersReport.model_json_schema()

    assert "runs" in schema["properties"]
    assert schema["properties"]["runs"]["type"] == "array"
