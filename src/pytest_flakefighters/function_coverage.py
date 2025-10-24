"""
This module implements the Profiler class to help measure function-level coverage.
"""

import ast
import os
import sys
from types import FrameType
from typing import Callable

from coverage import CoverageData


class Profiler:
    """
    Provides functionality to measure function-level coverage of a pytest test suite.

    :ivar coverage_data: The (potentially) covered lines for each module.
    :ivar function_defs: The lines that define a given function in a given module, accessed as
    `function_defs[module][function]`.
    """

    coverage_data: CoverageData = CoverageData(no_disk=True)
    function_defs: dict[str, dict[str, list[int]]] = {}

    def update_function_defs(self, module: str):
        """
        Extract the start and end lines for defined functions in the given module and add them to `function_defs`.

        :param module: The filepath of the module to process.
        """
        with open(module) as f:
            tree = ast.parse(f.read())
        self.function_defs[module] = {
            node.name: list(range(node.lineno, node.end_lineno + 1))
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

    def profile_fun_calls(self, frame: FrameType, event: str, arg: any) -> Callable:  # pylint: disable=W0613
        """
        Profile function to record the lines that define called functions.
        When `sys.setprofile(profiler.profile_fun_calls)` is enabled, this will be called every time a function is
        executed and update `coverage_data` accordingly.

        :param frame: The current stack frame.
        :param event: The type of profiling event that has occurred. One of [call, return, c_call, c_return, c_exception].
        :param arg: The event-specific argument, which changes based on the event string. Not used - required for
        compatibility with the profiler.
        """
        if event == "call":
            module = frame.f_code.co_filename
            if module not in self.function_defs and os.path.exists(module):
                self.update_function_defs(module)

            self.coverage_data.add_lines({module: self.function_defs.get(module, {}).get(frame.f_code.co_name, [])})
        return self.profile_fun_calls

    def start(self):
        """
        Start measuring coverage.
        """
        sys.setprofile(self.profile_fun_calls)

    def stop(self):
        """
        Stop measuring coverage.
        """
        sys.setprofile(None)

    def switch_context(self, context: str):
        """
        Set the context name of the coverage measurement.

        :param context: The context name to set.
        """
        self.coverage_data.set_context(context)

    def get_data(self):
        return self.coverage_data
