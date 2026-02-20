Configuration
================

The flakefighters plugin implements several cutting edge flaky test detection tools from the research community.
Each one is individually configurable and can be run individually or with other flakefighters.
By default, the plugin will only use the DeFlaker algorithm to classify flaky tests.
You can control which flakefighters to run and provide additional configuration options from your :code:`pyproject.toml` file by including sections of the following form for each flakefighter you want to run.
Here, :code:`<FlakeFighterClass>` is the class of the flakefighter you wish to configure as if you were going to import it into a source code file.

.. code-block:: toml

   [tool.pytest.ini_options.pytest_flakefighters.flakefighters.deflaker.DeFlaker]
   run_live=true # run the classifier immediately after each test

   [tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.TracebackMatching]
   run_live=false # run the classifier at the end of the test suite

   [tool.pytest.ini_options.pytest_flakefighters.flakefighters.traceback_matching.CosineSimilarity]
   run_live=false # run the classifier at the end of the test suite
   threshold=0.8 # Cosine similarity >= 0.8 is classed as a match

   [tool.pytest.ini_options.pytest_flakefighters.flakefighters.coverage_independence.CoverageIndependence]
   run_live=false # run the classifier at the end of the test suite
   threshold=0.1 # Distance <= 0.1 is classed as "similar"
   metric=hamming # Use Hamming distance
   linkage_method=complete # Use complete linkage for clustering

.. note::
   The above configuration is just an example meant to demonstrate the various parameters that can be supplied, and is not a recommendation or "default".

   You should choose the parameter values that are appropriate for your project, especially threshold values for **CosineSimilarity** and **CoverageIndependence**.

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
