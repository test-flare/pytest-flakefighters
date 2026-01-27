CI/CD Integration
=================

The `TestFLARE <https://test-flare.github.io/>`__ project is motivated by the fact that flaky tests can be particularly problematic for CI/CD pipelines.
The :code:`flakefighers` extension is therefore developed to integrate seamlessly with your existing pipelines and testing workflows.
If you already have a workflow that uses :code:`pytest`, all you need to do is include :code:`pytest-flakefighers` as a dependency.
The extension will then automatically be run as part of :code:`pytest`.

.. _remote-databases:

Remote Databases
----------------

When you run :code:`pytest`, the :code:`flakefighers` extension automatically saves the details of each run, including the classification result from each active flakefighter for each test.
This historical data can then be used on subsequent runs to inform flaky classification.
By default, this data is stored locally in an SQlite database called :code:`flakefighters.db`.
However, this is configurable using the :code:`--database-url` parameter, so you are free to save your data wherever you like.

If you are using the extension as part of your CI/CD pipeline and want to preserve the data between runs, you will need to use external service such as `Supabase <https://supabase.com/>`__ to host your database.
Fortunately, this is very straightforward as these services make make setup and connection very easy.
All you need to do is set up the database using your service of choice and pass the database URL into the :code:`--database-url` parameter.
You don't even need to create the tables yourself, as this will be done by the extension automatically on the first run!
Of course, for security reasons, we suggest making your URL a `secret <https://docs.github.com/en/actions/reference/security/secrets>`__ rather than including the raw string in your github workflow.

.. tip::
  If you don't need to preserve the data between CI/CD runs, but do want to inspect it, you can include it as an `artifact <https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts>`__.

Hybrid Databases
----------------

There may be situations where you sometimes want to store data locally and sometimes want to store it remotely.
For example, you may want your CI/CD runs to go into the remote database hosted externally, but your local runs to use a local database so that you don't clog up the remote database during debugging.
Depending on your workflow, you may even want to keep a local clone of your database and occasionally synchronise this with the remote database.
Fortunately, database providers such as Supabase make this a `relatively straightforward process <https://supabase.com/docs/guides/local-development/overview>`__.

.. warning::
  As with any such setting, synchronisation may result in conflicts or inconsistent behaviour if entries have been made into the remote database after you have cloned your local copy and before you have resynchronised.
  In particular, the results of flakefighters that examine historical runs can be confusing if historical runs that were performed before a particular :code:`pytest` run were not added until afterwards.
