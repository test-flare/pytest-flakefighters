"""
This module implements the Profiler class to help measure function-level coverage.
"""

import ast
import cProfile
import os
import pstats

from coverage import CoverageData


class Profiler:
    """
    Provides functionality to measure function-level coverage of a pytest test suite.

    :ivar coverage_data: The (potentially) covered lines for each module.
    :ivar function_defs: The lines that define a given function in a given module, accessed as
    `function_defs[module][function]`.
    """

    def __init__(self):
        self.coverage_data: CoverageData = CoverageData(no_disk=True)
        self.function_defs: dict[str, dict[str, list[int]]] = {}
        self.profiler = cProfile.Profile()

    def update_function_defs(self, module: str):
        """
        Extract the start and end lines for defined functions in the given module and add them to `function_defs`.

        :param module: The filepath of the module to process.
        """
        with open(module, encoding="utf8") as f:
            tree = ast.parse(f.read())
        self.function_defs[module] = {
            node.name: list(range(node.lineno, node.end_lineno + 1))
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

    def start(self):
        """
        Start measuring coverage.
        """
        self.profiler.enable()

    def stop(self):
        """
        Stop measuring coverage.
        """
        self.profiler.disable()
        p = pstats.Stats(self.profiler)
        for module, _, function in p.stats.keys():
            if module not in self.function_defs and os.path.exists(module):
                self.update_function_defs(module)
            self.coverage_data.add_lines({module: self.function_defs.get(module, {}).get(function, [])})

    def switch_context(self, context: str):
        """
        Set the context name of the coverage measurement.

        :param context: The context name to set.
        """
        self.profiler.clear()
        self.coverage_data.set_context(context)

    def get_data(self) -> CoverageData:
        """
        Return coverage data.
        """
        return self.coverage_data
