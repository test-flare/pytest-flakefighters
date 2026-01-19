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

In the example below, :code:`pytest` was called with the :code:`DeFlaker`, :code:`TracebackMatching` (at execution level), and :code:`CoverageIndependence` (at test level) flakefighters.
On the first execution of :code:`TestFlaky::test_flaky_example`, :code:`DeFlaker` classified the test failure as flaky, but :code:`TracebackMatching` classified it as genuine.
On the rerun, the outcome of :code:`DeFlaker` did not change, but :code:`TracebackMatching` classified it as flaky.
Finally, :code:`CoverageIndependence` classified the overall test as flaky.

..  code-block:: ini

  {
    "nodeid": "test_flaky.py::TestFlaky::test_flaky_example",
    "lineno": 5,
    "outcome": "failed",
    "setup": {"duration": 0.00024656900131958537, "outcome": "passed"},
    "call": {
      "duration": 0.000256097000601585,
      "outcome": "failed",
      "metadata": {
      "executions": [{
        "start_time": "2026-01-19 11:19:06.214221",
        "end_time": "2026-01-19 11:19:06.214703",
        "outcome": failed,
        "flakefighter_results": {"DeFlaker": "flaky", "TracebackMatching": "genuine"}
      }, {
        "start_time": "2026-01-19 11:19:06.264956",
        "end_time": "2026-01-19 11:19:06.265155",
        "outcome": failed,
        "flakefighter_results": {"DeFlaker": "flaky", "TracebackMatching": "flaky"}
      }
        ]
      }
    },
    "teardown": {"duration": 6.307100011326838e-05, "outcome": "passed"},
    "metadata": {
      "flakefighter_results": {"CoverageIndependence": "flaky"}
    }
  }

.. note::
  The :code:`pytest-json` extension is not officially supported, but the execution-level flakefighter results will be printed in a similar manner if you use this extension instead of the newer :code:`pytest-json-report`.
  Test-level flakefighter results will not be saved.

Writing to XML
--------------

The extension is designed to export results to JUnitXML when you run :code:`pytest` with the :code:`--junitxml` option.
The results will be saved in a :code:`<flakefighterresults>` element as a child of each :code:`<testcase>`.
Each execution-level result will be saved in an :code:`<execution>` element.
The test-level results will be saved in a :code:`<test>` element.

..  code-block:: ini

  <testcase classname="test_flaky_reruns.TestFlakyRuns" name="test_pass" time="0.001">
    <flakefighterresults>
      <execution outcome="failed" starttime="2026-01-19T11:44:58.123723" endtime="2026-01-19T11:44:58.124223">
        <DeFlaker>flaky</DeFlaker>
        <TracebackMatching>genuine</TracebackMatching>
      </execution>
      <execution outcome="failed" starttime="2026-01-19T11:44:58.173746" endtime="2026-01-19T11:44:58.173929">
        <DeFlaker>flaky</DeFlaker>
        <TracebackMatching>flaky</TracebackMatching>
      </execution>
      <test>
        <CoverageIndependence>flaky</CoverageIndependence>
      </test>
    </flakefighterresults>
  </testcase>
