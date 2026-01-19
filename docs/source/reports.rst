Reporting and Logging
=====================

The extension supports a range of reporting formats.
By default, flaky tests will be flagged in the short test summary info in the console output as shown below.
Genuine failures will show as :code:`FAILED` as normal.
Failures which have been classified as flaky by at least one active flakefighter will show as :code:`FLAKY`.

..  code-block:: ini

  ================================== short test summary info ==================================
  FLAKY test_flaky_reruns.py::TestFlakyRuns::test_create_or_delete - assert not True
  FAILED test_flaky_reruns.py::TestFlakyRuns::test_fail - assert False
  ================================ 2 failed, 1 passed in 1.13s ================================

Writing to JSON
---------------

The extension is designed to work with `pytest-json-report <https://pypi.org/project/pytest-json-report>`_ to create test reports as JSON.
To do this, you will need to :code:`pip install pytest-json-report`, after which you can run :code:`pytest` with the :code:`--json-report` option to save the test report to :code:`.report.json` by default.
The target path to save JSON report can be changed using the :code:`--json-report-file=PATH` option.
Each test :code:`call` will be assigned a :code:`metadata` field that records the execution-level flakefighter results for each (repeated) execution.
Each test will be assigned a :code:`metadata` field to record the test-level results.

..  code-block:: ini

  {
    "nodeid": "test_flaky_reruns.py::TestFlakyRuns::test_pass",
    "lineno": 5,
    "outcome": "passed",
    "keywords": ["test_pass", "TestFlakyRuns", "test_flaky_reruns.py", "flakefighters-test", ""],
    "setup": {"duration": 0.000145464000524953, "outcome": "passed"},
    "call": {
      "duration": 0.00017212499733432196,
      "outcome": "passed",
      "metadata": {
        "flakefighter_results": [
          [ # First execution
           {"name": "DeFlaker", "classification": "genuine"},
           {"name": "TracebackMatching", "classification": "genuine"},
           {"name": "CosineSimilarity", "classification": "genuine"}
          ],
          [ # Repeat 1
           {"name": "DeFlaker", "classification": "genuine"},
           {"name": "TracebackMatching", "classification": "genuine"},
           {"name": "CosineSimilarity", "classification": "genuine"}
          ],
          [ # Repeat 2
           {"name": "DeFlaker", "classification": "genuine"},
           {"name": "TracebackMatching", "classification": "genuine"},
           {"name": "CosineSimilarity", "classification": "genuine"}
          ]
        ]
      }
    },
    "teardown": {
      "duration": 5.345899990061298e-05,
      "outcome": "passed"
    },
    "metadata": {
      "flakefighter_results": [{"name": "CoverageIndependence","classification": "genuine"}]
    }
  }
