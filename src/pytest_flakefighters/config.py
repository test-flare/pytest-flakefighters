"""
This module defines all the configuration options in a dictionary.
Keys should be of the form `(--long-name, -L)` or just `(--long-name,)`.
Options can then be specified on the commandline as `--long-name` or in a configuration file as `long_name`.
Options specified on the commandline will override those specified in configuration files.
"""

import os

from pytest_flakefighters.rerun_strategies import All, FlakyFailure, PreviouslyFlaky

rerun_strategies = {"ALL": All, "FLAKY_FAILURE": FlakyFailure, "PREVIOUSLY_FLAKY": PreviouslyFlaky}


options = {
    ("--root",): {
        "dest": "root",
        "action": "store",
        "default": os.getcwd(),
        "help": "The root directory of the project. Defaults to the current working directory.",
    },
    ("--suppress-flaky-failures-exit-code",): {
        "dest": "suppress_flaky",
        "action": "store_true",
        "default": False,
        "help": "Return OK exit code if the only failures are flaky failures.",
    },
    ("--no-save",): {
        "action": "store_true",
        "default": False,
        "help": "Do not save this run to the database of previous flakefighters runs.",
    },
    ("--function-coverage",): {
        "action": "store_true",
        "default": False,
        "help": "Use function-level coverage instead of line coverage.",
    },
    ("--load-max-runs", "-M"): {
        "action": "store",
        "default": None,
        "help": "The maximum number of previous runs to consider.",
    },
    ("--database-url", "-D"): {
        "action": "store",
        "default": "sqlite:///flakefighters.db",
        "help": "The database URL. Defaults to 'flakefighters.db' in current working directory.",
    },
    ("--store-max-runs",): {
        "action": "store",
        "default": None,
        "type": int,
        "help": "The maximum number of previous flakefighters runs to store. Default is to store all.",
    },
    ("--max-reruns",): {
        "action": "store",
        "default": 0,
        "type": int,
        "help": "The maximum number of times to rerun tests. "
        "By default, only failing tests marked as flaky will be rerun. "
        "This can be changed with the --rerun-strategy parameter.",
    },
    ("--rerun-strategy",): {
        "action": "store",
        "type": str,
        "choices": list(rerun_strategies),
        "default": "FLAKY_FAILURE",
        "help": "The strategy used to determine which tests to rerun. Supported options are:\n  "
        + "\n  ".join(f"{name} - {strat.help()}" for name, strat in rerun_strategies.items()),
    },
    ("--time-immemorial",): {
        "action": "store",
        "default": None,
        "help": "How long to store flakefighters runs for, specified as `days:hours:minutes`. "
        "E.g. to store tests for one week, use 7:0:0.",
    },
    ("--display-outcomes", "-O"): {
        "action": "store",
        "type": int,
        "nargs": "?",  # Allows 0 or 1 arguments
        "const": 0,  # Value used if -O is present but no value is provided
        "default": 0,  # Value used if -O is not present at all
        "help": "Display historical test outcomes of the specified number of previous runs."
        "If no value is specified, then display only the current verdict.",
    },
    ("--display-verdicts",): {
        "action": "store_true",
        "default": False,
        "help": "Display the flaky classification verdicts alongside test outcomes.",
    },
    ("--flakefighters",): {
        "action": "store_true",
        "default": False,
        "help": "Enable the flakefighters plugin.",
    },
}
