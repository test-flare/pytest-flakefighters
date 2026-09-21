"""Serialize FlakeFighters database data to JSON."""

import json
from pathlib import Path
from typing import Iterable

from .models import FlakefightersReport, RunModel

def export_database_to_json(runs: Iterable, output_path: Path) -> None:
    """Export database runs to JSON."""
    report = FlakefightersReport(runs=[RunModel.model_validate(run) for run in runs])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

def export_json_schema(output_path: Path) -> None:
    """Export the JSON Schema describing a FlakeFighters report."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            FlakefightersReport.model_json_schema(),
            indent=2,
        ),
        encoding="utf-8",
    )
