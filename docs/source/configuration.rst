Configuration
================

The flakefighters plugin implements several cutting edge flaky test detection tools from the research community.
Each one is individually configurable and can be run individually or with other flakefighters.
You can control which flakefighters to run and provide additional configuration options from your :code:`pyproject.toml` file by including sections of the following form for each flakefighter you want to run.
Here, :code:`<FlakeFighterName>` is the class name of the flakefighter you wish to configure, assuming the class is in the :code:`pytest-flakefighters/flakefighters` directory.
::
[tool.pytest.ini_options.pytest_flakefighters.<FlakeFighterName>]
run_live=[true/false]
option1=value1
option2=value2
...

Every flakefighter will have a :code:`run_live` option, which can be set to :code:`true` to classify each test execution as flaky immediately after it is run, or :code:`false` to clasify all tests at once at the end, although individual flakefighters may only support one particular option.
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
