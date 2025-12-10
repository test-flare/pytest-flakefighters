Getting Started
================

Installation
-----------------
* We currently support Python versions 3.10, 3.11, 3.12, and 3.13.

* The Flakefighters plugin can be installed through the `Python Package Index (PyPI)`_ (recommended), or directly from source (recommended for contributors).

.. _Python Package Index (PyPI): https://pypi.org/project/pytest-flakefighters

Method 1: Installing via pip
..............................

To install the Causal Testing Framework using :code:`pip` for the latest stable version::

    pip install pytest-flakefighters

The plugin will then automatically run as part of `pytest`.

If you also want to install the framework with (optional) development packages/tools::

    pip install pytest-flakefighters[dev]


Method 2: Installing via Source (For Developers/Contributors)
...............................................................

If you're planning to contribute to the project or need an editable installation for development, you can install directly from source::

    git clone https://github.com/test-flare/pytest-flakefighters.git
    cd pytest-flakefighters

then, to install a specific release::

    git fetch --all --tags --prune
    git checkout tags/<tag> -b <branch>
    pip install . # For core API only
    pip install -e . # For editable install, useful for development work

e.g. version `1.0.0`::

    git fetch --all --tags --prune
    git checkout tags/1.0.0 -b version
    pip install .

or to install the latest development version::

    pip install .

To also install developer tools::

    pip install -e .[dev]

Verifying Your Installation
-----------------------------

After installation, verify that the framework is installed correctly in your environment::

    python -c "import pytest_flakefighters; print(pytest_flakefighters.__version__)"

Next Steps
-----------

* Check out the :doc:`tutorials` to learn how to use the framework.
* Read about :doc:`modules/causal_specification` to understand causal specifications and :doc:`modules/causal_testing` for the end-to-end causal testing process.
* Try the command-line interface for quick and simple testing::

    python -m causal_testing test --help
