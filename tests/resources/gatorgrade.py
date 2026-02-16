import os

import pytest


@pytest.mark.parametrize(
    "assignment_path,expected_output_and_freqs",
    [
        (
            "test_assignment",
            [
                ("Complete all TODOs", 2),
                ("Use an if statement", 1),
                ("✓", 3),
                ("✕", 0),
                ("Passed 3/3 (100%) of checks", 1),
            ],
        )
    ],
)
def test_full_integration_creates_valid_output(assignment_path, expected_output_and_freqs):
    """Simplified version of
    https://github.com/GatorEducator/gatorgrade/blob/91cb86d5383675c5bc3c95363bc29b45108b2e29/tests/test_main.py#L70
    which initially broke the plugin due to the test IDs contaning [] characters from the parameterisation."""
    with open(os.path.join(assignment_path, "result.txt"), encoding="utf8") as f:
        result = f.read()
    for output, freq in expected_output_and_freqs:
        assert result.count(output) == freq
