.. pytest-flakefighters documentation master file, created by
   sphinx-quickstart on Thu Oct  1 00:43:18 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pytest Flakefighters
===============================================================

|status|
|ci-tests|
|code-cov|
|pypi|
|docs|
|python|
|license|


Motivation
----------

:term:`Flaky tests` intermittently pass and fail without changes to test or project source code, often without an obvious cause.
When flaky tests proliferate, developers may loose faith in their test suites, potentially exposing end-users to the consequences of software failures.

Pytest Plugin
----------------

.. _pytest-flakefighters: https://github.com/test-flare/pytest-flakefighters
.. _pytest-rerunfailures: https://github.com/pytest-dev/pytest-rerunfailures
.. _pytest-flaky: https://github.com/box/flaky
.. _pytest-flakefinder: https://github.com/dropbox/pytest-flakefinder
.. _pytest-replay: https://github.com/ESSS/pytest-replay
.. _pytest-xdist: https://github.com/pytest-dev/pytest-xdist

Flakefighters is a pytest plugin developed as part of the `TestFLARE <https://test-flare.github.io/>`__ project.
The plugin provides a "Swiss army knife" of techniques (called flakefighters) to detect flaky tests.
Where existing flaky test plugins such as `pytest-rerunfailures`_, `pytest-flaky`_ are primarily focused on rerunning (potentially) flaky tests until they pass, our main aim is to identify flaky tests by classifying test failures as genuine or flaky.
The `pytest-flakefinder`_ plugin does this by simply rerunning tests multiple times and observing the result.
By contrast, Flakefighters incorporates several cutting edge flaky test detection techniques from research to automatically classify test failures as either genuine: indicating either a fault in the code or a mis-specified test case, or flaky: indicating a test with a nondeterministic outcome.
Flaky tests are then reported separately in the test report, and can be optionally rerun or suppressed so they don't block CI/CD pipelines.

+------------------------+--------------------------------------------------------------+---------------------------------------------+------------------------+--------------------------------------------------+----------------------------------------------------------------+
| Feature                | `pytest-flakefighters`_                                      | `pytest-rerunfailures`_                     | `pytest-flaky`_        | `pytest-flakefinder`_                            | `pytest-replay`_                                               |
+========================+==============================================================+=============================================+========================+==================================================+================================================================+
| **Purpose**            | Clasify test failures as genuine or flaky                    | Rerun failing tests in case they are flaky  | Decorator-based reruns | Copy tests to observe nondeterministic outcomes  | Reproduce flaky failures from CI when running tests with xdist |
+------------------------+--------------------------------------------------------------+---------------------------------------------+---------------------------------------------------------------------------+----------------------------------------------------------------+
| **Detection Method**   | DeFlaker algorithm + coverage analysis                       | None                                        | None                   | Reruns                                           | None                                                           |
+------------------------+--------------------------------------------------------------+---------------------------------------------+---------------------------------------------------------------------------+----------------------------------------------------------------+
| **Reporting**          | Terminal, HTML, JSON, JUnitXML                               | Terminal                                    | Terminal               | Terminal                                         | Terminal                                                       |
+------------------------+--------------------------------------------------------------+---------------------------------------------+---------------------------------------------------------------------------+----------------------------------------------------------------+
| **History Tracking**   | Database of test outcomes over commits                       | None                                        | None                   | None                                             | None                                                           |
+------------------------+--------------------------------------------------------------+---------------------------------------------+---------------------------------------------------------------------------+----------------------------------------------------------------+
| **Rerun Option**       | Optional                                                     | Required                                    | Required               | Required                                         | Required                                                       |
+------------------------+--------------------------------------------------------------+---------------------------------------------+---------------------------------------------------------------------------+----------------------------------------------------------------+
| **Suppression Option** | Optional                                                     | None                                        | None                   | None                                             | None                                                           |
+------------------------+--------------------------------------------------------------+---------------------------------------------+---------------------------------------------------------------------------+----------------------------------------------------------------+
| **Debugging support**  | Flakefighter results give insight into *why* tests are flaky | None                                        | None                   | None                                             | Reliable reproduction of flaky failures                        |
+------------------------+--------------------------------------------------------------+---------------------------------------------+---------------------------------------------------------------------------+----------------------------------------------------------------+

Key features of pytest-flakefighters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use pytest-flakefighters when you want to:

* **Understand WHY** tests are flaky, not just hide the symptoms
* **Classify** flaky tests by root cause (coverage-independent, traceback-matched, etc.)
* **Track** test flakiness over time and across commits
* **Make informed decisions** about whether failures are legitimate

When to use alternatives
^^^^^^^^^^^^^^^^^^^^^^^^

* `pytest-rerunfailures`_ Quick fix for CI builds
* `pytest-flaky`_ A few tests are known to be flaky
* `pytest-flakefinder`_ Brute force search for flaky tests
* `pytest-replay`_ Debugging specific flaky failures

Can They Work Together?
^^^^^^^^^^^^^^^^^^^^^^^

Yes! pytest-flakefighters can be combined with other flaky test plugins:

* Use `pytest-flakefighters` to identify and classify flaky tests
* Use `pytest-rerunfailures`_ or **pytest-flaky** as a temporary measure while fixing them
* Use `pytest-replay`_ to debug specific instances identified by flakefighters
* Use `pytest-xdist` to randomise the order or your test cases

----

*For more information on flaky test management best practices, see the* `pytest documentation <https://docs.pytest.org/en/stable/explanation/flaky.html>`_.


.. toctree::
   :hidden:
   :caption: Home

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Introduction

   installation
   configuration
   custom_flakefighters
   reports
   ci_cd


.. toctree::
   :maxdepth: 2
   :caption: API
   :hidden:
   :titlesonly:

   /autoapi/index

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Glossary

   glossary

.. toctree::
  :hidden:
  :maxdepth: 1
  :caption: Development

  /dev/version_release
  /dev/documentation
  /dev/actions_and_webhooks

.. toctree::
   :caption: Useful Links
   :hidden:
   :maxdepth: 2

   Source code <https://github.com/test-flare/pytest-flakefighters/>
   Documentation <https://causal-testing-framework.readthedocs.io/en/latest/>
   PyPI <https://pypi.org/project/pytest-flakefighters/>
   TestFLARE Homepage <https://test-flare.github.io/>

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Acknowledgements

   acknowlegements

.. Define variables for our GH badges

.. |ci-tests| image:: https://github.com/test-flare/pytest-flakefighters/actions/workflows/ci-tests.yaml/badge.svg
   :target: https://github.com/test-flare/pytest-flakefighters/actions/workflows/ci-tests.yaml
   :alt: Continuous Integration Tests

.. |code-cov| image:: https://codecov.io/gh/test-flare/pytest-flakefighters/branch/main/graph/badge.svg?token=04ijFVrb4a
   :target: https://codecov.io/gh/test-flare/pytest-flakefighters
   :alt: Code coverage

.. |docs| image:: https://readthedocs.org/projects/pytest-flakefighters/badge/?version=latest
   :target: https://pytest-flakefighters.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation

.. |python| image:: https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Ftest-flare%2Fpytest-flakefighters%2Fmain%2Fpyproject.toml&query=%24.project%5B'requires-python'%5D&label=python
   :target: https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Ftest-flare%2Fpytest-flakefighters%2Fmain%2Fpyproject.toml&query=%24.project%5B'requires-python'%5D&label=python
   :alt: Python

.. |status| image:: https://www.repostatus.org/badges/latest/active.svg
   :target: https://www.repostatus.org/#active
   :alt: Status

.. |pypi| image:: https://img.shields.io/pypi/v/pytest-flakefighters
  :target: https://pypi.org/project/pytest-flakefighters
  :alt: PyPI

.. |license| image:: https://img.shields.io/github/license/test-flare/pytest-flakefighters
   :target: https://github.com/test-flare/pytest-flakefighters
   :alt: License
