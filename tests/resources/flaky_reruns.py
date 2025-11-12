import os
from pathlib import Path


class FlakyReruns:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)

    def create_or_delete(self) -> bool:
        file_exists = os.path.exists(self.filepath)
        # Delete the file if it exists, and create it otherwise
        # This has to be a single line otherwise you get different coverage for passing and failing runs
        os.remove(self.filepath) if file_exists else self.filepath.touch()
        return file_exists


class TestFlakyRuns:

    def test_create_or_delete(self):
        flaky = FlakyReruns("test.txt")
        result = flaky.create_or_delete()
        assert result
