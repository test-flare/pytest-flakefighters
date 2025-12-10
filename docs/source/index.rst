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

The Extension
-------------

Flakefighters is a pytest extension that provides a "Swiss army knife" of techniques to detect flaky tests.
The extension incorporates several cutting edge flaky test detection techniques from research to automatically classify test failures as either genuine: indicating either a fault in the code or a mis-specified test case, or flaky: indicating a test with a nondeterministic outcome.
Flaky tests are then reported separately in the test report, and can be optionally suppressed so they don't block CI/CD pipelines.


.. toctree::
   :hidden:
   :caption: Home

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Introduction

   installation
   configuration


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
