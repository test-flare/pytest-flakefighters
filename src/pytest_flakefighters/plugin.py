"""
This module implements the DeFlaker algorithm [Bell et al. 10.1145/3180155.3180164] as a pytest plugin.
"""

from datetime import datetime
from enum import Enum
from typing import Union
from xml.etree import ElementTree as ET

import coverage
import pytest
from _pytest.runner import runtestprotocol

from pytest_flakefighters.database_management import (
    ActiveFlakeFighter,
    Database,
    Run,
    Test,
    TestException,
    TestExecution,
    TracebackEntry,
)
from pytest_flakefighters.flakefighters.abstract_flakefighter import FlakeFighter
from pytest_flakefighters.function_coverage import Profiler


class RerunStrategy(Enum):
    """
    Enum for supported test rerunning strategies.
    :cvar ALL: Rerun all tests, regardless of outcome.
    :cvar FLAKY_FAILURE: Rerun failing tests marked as flaky.
    :cvar PREVIOUS_FLAKY: Rerun tests that have previously been marked as flaky as well as newly failing flaky tests.
    """

    ALL = "ALL"
    FLAKY_FAILURE = "FLAKY_FAILURE"
    PREVIOUSLY_FLAKY = "PREVIOUSLY_FLAKY"


class FlakeFighterPlugin:  # pylint: disable=R0902
    """
    The main plugin to manage the various FlakeFighter tools.
    """

    def __init__(  # pylint: disable=R0913,R0917
        self,
        root: str,
        database: Database,
        cov: Union[coverage.Coverage, Profiler],
        flakefighters: list[FlakeFighter],
        save_run: bool = True,
        rerun_strategy: RerunStrategy = RerunStrategy.FLAKY_FAILURE,
        display_outcomes: int = 0,
        display_verdicts: bool = False,
    ):
        self.root = root
        self.database = database
        self.cov = cov
        self.flakefighters = flakefighters
        self.save_run = save_run
        self.rerun_strategy = rerun_strategy
        self.test_reports = {}
        self.display_verdicts = display_verdicts
        self.display_outcomes = display_outcomes

        self.run = Run(  # pylint: disable=E1123
            root=root,
            active_flakefighters=[
                ActiveFlakeFighter(name=f.__class__.__name__, params=f.params()) for f in flakefighters
            ],
            start_time=datetime.now(),
        )

    def pytest_sessionstart(self, session: pytest.Session):  # pylint: disable=unused-argument
        """
        Start the coverage measurement before tests are collected so we measure class and method definitions as covered.
        :param session: The session.
        """
        self.cov.start()
        self.cov.switch_context("collection")  # pragma: no cover

    def pytest_collection_finish(self, session: pytest.Session):  # pylint: disable=unused-argument
        """
        Stop the coverage measurement after tests are collected.
        :param session: The session.
        """
        # Line cannot appear as covered on our tests because the coverage measurement is leaking into the self.cov
        self.cov.switch_context(None)  # pragma: no cover
        self.cov.stop()  # pragma: no cover

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item: pytest.Item):
        """
        Start the coverage measurement and label the coverage for the current test, run the test,
        then stop coverage measurement.

        :param item: The item.
        """
        item.start = datetime.now().timestamp()
        self.cov.start()
        # Lines cannot appear as covered on our tests because the coverage measurement is leaking into the self.cov
        self.cov.switch_context(item.nodeid)  # pragma: no cover
        yield  # pragma: no cover
        self.cov.stop()  # pragma: no cover
        item.stop = datetime.now().timestamp()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo):  # pylint: disable=unused-argument
        """
        Called after a test execution call (setup, call, teardown)
        to create a TestReport.

        :param item: The item.
        :param call: The call info.
        """
        outcome = yield
        report = outcome.get_result()
        excinfo = call.excinfo
        if excinfo is not None and call.when == "call":
            report.exception = TestException(  # pylint: disable=E1123
                name=excinfo.type.__name__,
                traceback=[
                    TracebackEntry(
                        path=str(entry.path),
                        lineno=entry.lineno,
                        colno=entry.colno,
                        statement=str(entry.statement),
                        source=str(entry.source),
                    )
                    for entry in excinfo.traceback
                    if entry.path
                ],
            )
        else:
            report.exception = None

    def pytest_runtest_protocol(self, item: pytest.Item, nextitem: pytest.Item) -> bool:
        """
        Rerun flaky tests. Follows a similar control logic to the pytest-rerunfailures plugin.

        :param item: The item.
        :param nextitem: The next item.

        :return: The return value is not used, but only stops further processing.
        """
        item.execution_count = 0
        skipped = False

        fspath, line_inx, _ = item.location

        test = Test(  # pylint: disable=E1123
            name=item.nodeid,
            fspath=fspath,
            line_no=line_inx + 1,  # need to add one to the line index because this indexes from zero
            skipped=skipped,
        )
        self.run.tests.append(test)

        for _ in range(self.rerun_strategy.max_reruns + 1):
            item.execution_count += 1
            item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
            reports = runtestprotocol(item, nextitem=nextitem, log=False)

            for report in reports:  # up to 3 reports: setup, call, teardown
                if report.when == "setup" and report.skipped:
                    skipped = True
                if report.when == "call":
                    line_coverage = self.cov.get_data()
                    line_coverage.set_query_contexts(["collection", item.nodeid])
                    captured_output = dict(report.sections)
                    test_execution = TestExecution(  # pylint: disable=E1123
                        outcome=report.outcome,
                        stdout=captured_output.get("stdout"),
                        stderr=captured_output.get("stderr"),
                        report=str(report.longrepr),
                        start_time=datetime.fromtimestamp(item.start),
                        end_time=datetime.fromtimestamp(item.stop),
                        coverage={
                            file_path: line_coverage.lines(file_path) for file_path in line_coverage.measured_files()
                        },
                        exception=report.exception,
                    )
                    test.executions.append(test_execution)
                    for ff in filter(lambda ff: ff.run_live, self.flakefighters):
                        ff.flaky_test_live(test_execution)
                    self.test_reports[item.nodeid] = report
                    report.flaky = any(result.flaky for result in test_execution.flakefighter_results)
                    # Limited pytest-json support
                    report.stage_metadata = {
                        "executions": [
                            {
                                "start_time": x.start_time.isoformat(),
                                "end_time": x.end_time.isoformat(),
                                "outcome": test_execution.outcome,
                                "flakefighter_results": {r.name: r.classification for r in x.flakefighter_results},
                            }
                            for x in test.executions
                        ],
                    }
                    # html
                    if hasattr(report, "extras"):
                        report.extras.append(
                            {
                                "content": f"""
                                <h4>Flakefighter Results</h4>
                                <div id="ff-{report.nodeid.replace("::", "_")}"></div>
                                <table style="width:100%"><tbody><tr>"""
                                + "".join(
                                    [
                                        f"""
                                        <td>
                                        <p><strong>Start time:</strong> {execution.start_time}</p>
                                        <p><strong>End time:</strong> {execution.end_time}</p>
                                        <p><strong>Outcome:</strong> {execution.outcome}</p>
                                        <p><strong>Flakefighter Results:</strong></p>
                                        <ul>
                                        {''.join(['<li><strong>'+result.name+':</strong> '+result.classification+'</li>'
                                        for result in execution.flakefighter_results])}
                                        </ul>
                                        </td>
                                        """
                                        for execution in test.executions
                                    ]
                                )
                                + "</tr></tbody></table>",
                                "extension": "html",
                                "format_type": "html",
                                "mime_type": "text/html",
                            }
                        )
                    if item.execution_count <= self.rerun_strategy.max_reruns and self.rerun_strategy.rerun(report):
                        break  # trigger rerun

                item.ihook.pytest_runtest_logreport(report=report)
            else:
                break  # Skip further reruns

        item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
        return True

    def pytest_report_teststatus(
        self, report: pytest.TestReport, config: pytest.Config  # pylint: disable=unused-argument
    ) -> tuple[str, str, str]:
        """
        Report flaky failures as such.
        :param report: The report object whose status is to be returned.
        :param config: The pytest config object.
        :returns: The test status.
        """
        if getattr(report, "flaky", False) and not report.passed:
            return report.outcome, "F", ("FLAKY", {"yellow": True})
        return None

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtestloop(self, session: pytest.Session):  # pylint: disable=unused-argument
        """
        Run postprocessing flakefighters.
        :param session: The pytest session object.
        """
        yield
        for ff in filter(lambda ff: not ff.run_live, self.flakefighters):
            ff.flaky_tests_post(self.run)
        for test in self.run.tests:
            self.test_reports[test.name].flakefighter_results = [r.to_dict() for r in test.flakefighter_results]

    @pytest.hookimpl(optionalhook=True)
    def pytest_json_modifyreport(self, json_report: dict):
        """
        Add flakefighter results to the pytest-json-report report.

        :param json_report: The report dict.
        """
        for t in json_report.get("tests", []):
            t["call"]["metadata"] = self.test_reports[t["nodeid"]].stage_metadata

            t["metadata"] = t.get("metadata", {}) | {
                "flakefighter_results": {
                    r.name: r.classification for r in self.test_reports[t["nodeid"]].flakefighter_results
                }
            }

    def build_outcome_string(self, test: Test) -> str:
        """
        Construct a string to represent previous flakefighter outcomes for a given test and its associated executions.

        :param test: The test case.
        """
        result_string = []
        if test.flakefighter_results:
            if self.display_verdicts:
                result_string.append(
                    "Overall\n" + "\n".join(f"  {f.name}: {f.classification}" for f in test.flakefighter_results) + "\n"
                )
        for i, execution in enumerate(test.executions):
            if execution.flakefighter_results:
                if self.display_verdicts:
                    result_string.append(
                        f"Execution {i}: {execution.outcome}\n"
                        + "\n".join(
                            f"  {f.name}: {'flaky' if f.flaky else 'genuine'}" for f in execution.flakefighter_results
                        )
                    )
                else:
                    result_string.append(f"Execution {i}: {execution.outcome}")
        return "\n".join(result_string)

    def modify_xml(self, xml_path: str):
        """
        Modify the JUnitXML file to add the flakefighter results for each test.

        :param xml_path: The path of the saved XML file.
        """
        tree = ET.parse(xml_path)
        for testsuite in tree.getroot().findall("testsuite"):
            for testcase in testsuite.findall("testcase"):
                module, classname = testcase.get("classname").split(".")
                nodeid = "::".join([f"{module}.py", classname, testcase.get("name")])
                flakefighter_results = ET.SubElement(testcase, "flakefighterresults")
                if nodeid in self.test_reports:
                    for execution in self.test_reports[nodeid].stage_metadata["executions"]:
                        execution_results = ET.Element(
                            "execution",
                            {
                                "outcome": execution["outcome"],
                                "starttime": execution["start_time"],
                                "endtime": execution["end_time"],
                            },
                        )
                        flakefighter_results.append(execution_results)
                        for name, classification in execution["flakefighter_results"].items():
                            ET.SubElement(execution_results, name).text = classification
                    test_results = ET.SubElement(flakefighter_results, "test")
                    for result in self.test_reports[nodeid].flakefighter_results:
                        ET.SubElement(test_results, result["name"]).text = result["classification"]

        tree.write(xml_path)

    @pytest.hookimpl(optionalhook=True)
    def pytest_html_results_summary(
        self, prefix: list, summary: list, postfix: list
    ):  # pylint: disable=unused-argument
        """
        Add the test-level flakefighter results.
        :param prefix: The prefix content. UNUSED.
        :param prefix: The summary content. UNUSED.
        :param prefix: The postfix content.
        """
        postfix.extend(
            [
                "<h2>Test-level flakefighter results</h2>",
                "<table>",
                "<thead><tr><td>Test</td><td>Flakefighter results</td></tr></thead>",
                "<tbody>",
            ]
            + [
                f"<tr><td>{nodeid}</td><td>"
                + "".join(
                    [
                        f"""<ul>
                            {''.join(['<li><strong>'+result['name']+':</strong> '+result['classification']+'</li>'
                                for result in report.flakefighter_results])}
                            </ul>"""
                    ]
                )
                + "</td></tr>"
                for nodeid, report in self.test_reports.items()
            ]
            + [
                "</tbody>",
                "</table>",
            ]
        )

    def pytest_sessionfinish(
        self,
        session: pytest.Session,
        exitstatus: pytest.ExitCode,  # pylint: disable=unused-argument
    ) -> None:
        """Called after whole test run finished, right before returning the exit status to the system.
        :param session: The pytest session object.
        :param exitstatus: The status which pytest will return to the system.
        """

        if session.config.option.xmlpath:
            self.modify_xml(session.config.option.xmlpath)

        if self.display_outcomes:
            for run in [self.run] + self.database.load_runs(self.display_outcomes):
                for test in run.tests:
                    if test.name in self.test_reports:
                        self.test_reports[test.name].sections.append(
                            (
                                f"Flakefighter Verdicts {run.start_time if run != self.run else '(Current)'}",
                                self.build_outcome_string(test),
                            )
                        )

        genuine_failure_observed = any(
            not test.flaky for test in self.run.tests if any(e.outcome != "passed" for e in test.executions)
        )

        if (
            session.config.option.suppress_flaky
            and session.exitstatus == pytest.ExitCode.TESTS_FAILED
            and not genuine_failure_observed
        ):
            session.exitstatus = pytest.ExitCode.OK

        if self.save_run:
            self.database.save(self.run)
        self.database.engine.dispose()
