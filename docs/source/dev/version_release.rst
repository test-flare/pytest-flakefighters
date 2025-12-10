Version Releases
================

This project follows the `Semantic Versioning 2.0.0 <https://semver.org/>`_ style for code releases.
This page describes the release process for a new framework version on the `Project Github <https://github.com/test-flare/pytest-flakefighters>`_.

How to release
--------------

#. Once your PR(s) are merged, navigate to https://github.com/test-flare/pytest-flakefighters/releases, which can be found on the right hand side of the projects Github main page by clicking on 'Releases'.

#. Press the **Draft a new release** button in the top right of the releases page.

#. Press the **Choose a tag** button and add the new version following the Semantic Version guidelines.
   Please include the 'v' before the tag, e.g. **v0.0.0**.

#. Enter the same tag name into the **Release Title** box.

#. Press **Generate Release Notes** button.

#. Add any additional information that may be helpful to the release notes. If there are breaking changes for example, which modules will they affect?

#. Ensure the **Set as the latest release** checkbox is selected.

#. Press publish release.

#. Check that the Github Action worker, found in the `Actions tab <https://github.com/test-flare/pytest-flakefighters/actions>`_ has successfully completed. The typical time to publish to PyPI is around 2 minutes.

#. Check on the projects `PyPI page <https://pypi.org/project/pytest-flakefighters/>`_ that the latest release is ready!

From here the latest version can be installed using the common pip version commands. e.g. ``pip install pytest-flakefighters==0.0.0``
