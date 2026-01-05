Github Actions and Webhooks
===========================

Actions
--------------

The Causal Testing Framework makes use of 5 `Github Actions <https://github.com/features/actions>`_,
which can be found in the
`.github/workflows <https://github.com/test-flare/pytest-flakefighters/tree/main/.github/workflows>`_ directory. These include:

#.  ``ci-tests-drafts.yaml``, which runs continuous integration (CI) tests on each on each draft pull request.

#.  ``ci-tests.yaml``, which runs continuous integration (CI) tests on each on each pull request.

#.  ``ci-mega-linter.yaml``, which runs linting on each pull request.

#.  ``publish-to-pypi.yaml``, runs when a new version tag is pushed and publishes that tag version to PyPI.

Webhooks
---------------

We also use two `Webhooks <https://docs.github.com/en/webhooks-and-events/webhooks/about-webhooks>`_, which can
be found in the `project settings <https://github.com/test-flare/pytest-flakefighters/settings>`_ on Github. These
include:


#.  `Codecov <https://github.com/codecov>`_

#.  `Read the Docs <https://github.com/readthedocs>`_
