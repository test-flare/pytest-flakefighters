Configuration
================

The flakefighters plugin implements several cutting edge flaky test detection tools from the research community.
Each one is individually configurable and can be run individually or with other flakefighters.
You can control which flakefighters to run and provide additional configuration options from your :code:`pyproject.toml` file by including sections of the following form for each flakefighter you want to run.
Here, :code:`<FlakeFighterClass>` is the class of the flakefighter you wish to configure as if you were going to import it into a source code file.

..  code-block:: ini

  [tool.pytest.ini_options.pytest_flakefighters.<FlakeFighterClass>]
  run_live=[true/false]
  option1=value1
  option2=value2
  ...

Every flakefighter has a :code:`run_live` option, which can be set to :code:`true` to classify each test execution as flaky immediately after it is run, or :code:`false` to clasify all tests at once at the end, although individual flakefighters may only support one of these.
Individual flakefighters have their own configurable options.
These are detailed below.

.. autoclass:: pytest_flakefighters.flakefighters.coverage_independence.CoverageIndependence
  :noindex:
.. autoclass:: pytest_flakefighters.flakefighters.deflaker.DeFlaker
  :noindex:
.. autoclass:: pytest_flakefighters.flakefighters.traceback_matching.TracebackMatching
  :noindex:
.. autoclass:: pytest_flakefighters.flakefighters.traceback_matching.CosineSimilarity
  :noindex:
