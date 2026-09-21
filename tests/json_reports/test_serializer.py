"""Tests for FlakeFighters JSON serialization."""

import json
from datetime import datetime

from pytest_flakefighters.json_reports.serializer import (
    export_database_to_json,
    export_json_schema,
)


def test_export_database_to_json(tmp_path):
    """Test exporting database runs to JSON."""

    class Run:
        id = 1
        start_time = datetime(2026, 9, 21, 10, 0)
        created_at = datetime(2026, 9, 21, 10, 1)
        root = "/project"
        commit_sha = "abc123"
        active_flakefighters = []
        tests = []

    output_path = tmp_path / "flakefighters.json"

    export_database_to_json([Run()], output_path)

    data = json.loads(output_path.read_text())

    assert data["runs"][0]["id"] == 1
    assert data["runs"][0]["commit_sha"] == "abc123"


def test_export_json_schema(tmp_path):
    """Test exporting the JSON Schema."""

    output_path = tmp_path / "flakefighters.schema.json"

    export_json_schema(output_path)

    schema = json.loads(output_path.read_text())

    assert "runs" in schema["properties"]
    assert schema["properties"]["runs"]["type"] == "array"
