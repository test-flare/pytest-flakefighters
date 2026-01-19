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

In the example below, :code:`pytest` was called with the :code:`DeFlaker`, :code:`TracebackMatching`, and :code:`CoverageIndependence` flakefighters.
On the first execution of :code:`TestFlaky::test_flaky_example`, :code:`DeFlaker` classified the test failure as flaky, but :code:`TracebackMatching` classified it as genuine.
On the rerun, the outcome of :code:`DeFlaker` did not change, but :code:`TracebackMatching` classified it as flaky.
Finally, :code:`CoverageIndependence` classified the overall test as flaky.

..  code-block:: ini

  {
    "nodeid": "test_flaky.py::TestFlaky::test_flaky_example",
    "lineno": 5,
    "outcome": "failed",
    "setup": {"duration": 0.000145464000524953, "outcome": "passed"},
    "call": {
      "duration": 0.00017212499733432196,
      "outcome": "failed",
      "metadata": {
        "flakefighter_results": [
          [ # First execution
           {"name": "DeFlaker", "classification": "flaky"},
           {"name": "TracebackMatching", "classification": "genuine"},
          ],
          [ # Rerun
           {"name": "DeFlaker", "classification": "flaky"},
           {"name": "TracebackMatching", "classification": "flaky"},
          ],
        ]
      }
    },
    "teardown": {
      "duration": 5.345899990061298e-05,
      "outcome": "passed"
    },
    "metadata": {
      "flakefighter_results": [{"name": "CoverageIndependence","classification": "flaky"}]
    }
  }
