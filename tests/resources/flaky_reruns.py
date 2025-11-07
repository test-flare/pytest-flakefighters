import os


class FlakyReruns:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def create_or_delete(self) -> bool:
        file_exists = os.path.exists(self.filepath)
        with open(self.filepath, "w") as f:
            print("", file=f)
        return file_exists


class TestFlakyRuns:

    def test_create_or_delete(self):
        flaky = FlakyReruns("test.txt")
        result = flaky.create_or_delete()
        assert result
