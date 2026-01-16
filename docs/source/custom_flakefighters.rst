Custom Flakefighters
====================

In addition to the flakefighters that are distributed with the extension, you can also define your own custom flakefighter classes.
To do this, you simply need to extensd the :code:`Flakefighter` class and implement the abstract methods.
For example, see below

..  code-block:: python

  from pytest_flakefighters.flakefighters.abstract_flakefighter import(
    FlakeFighter,
    FlakefighterResult
  )
  from pytest_flakefighters.database_management import Run, TestExecution


  class CustomFlakefighter(FlakeFighter):

      def __init__(self, run_live: bool, custom_arg: str):
          super().__init__(run_live)
          self.custom_arg = custom_arg

      @classmethod
      def from_config(cls, config: dict):
          """
          Factory method to create a new instance from a pytest configuration.
          """
          return CustomFlakefighter(
              run_live=config.get("run_live", True),
              custom_arg=config.get("custom_arg", ""),
          )

      def params(self):
          """
          Convert the key parameters into a dictionary so that the object can be replicated.
          You do not need to include the value of self.run_live here as that is recorded
          separately.
          :return A dictionary of the parameters used to create the object.
          """
          return {"custom_arg": self.custom_arg}

      def flaky_test_live(self, execution: TestExecution):
          """
          Detect whether a given test execution is flaky and append the result to its
          `flakefighter_results` attribute.
          :param execution: The test execution to classify.
          """
          execution.flakefighter_results.append(
              FlakefighterResult(
                  name=self.__class__.__name__,
                  # Implement logic to determine this result at *execution level*
                  flaky=True,
              )
          )

      def flaky_tests_post(self, run: Run):
          """
          Go through each test in the test suite and append the result to its
          `flakefighter_results` attribute.
          :param run: Run object representing the pytest run, with tests
          accessible through run.tests.
          """
          for test in run.tests:
              test.flakefighter_results.append(
                  FlakefighterResult(
                      name=self.__class__.__name__,
                      # Implement logic to determine this result at *test level*
                      # In many cases, it will be sufficient to test whether
                      # any executions are flaky
                      flaky=True
                  )
              )

Once you have implemented your flakefighter class, you will need to register it as an extra entry point in your :code:`pyproject.toml` file so that the plugin can find it.
For example, if you had defined your :code:`CustomFlakefighter` class in a module called :code:`custom_flakefighter`, you would register it as follows.

..  code-block:: ini

  [project.entry-points."pytest_flakefighters"]
  CustomFlakefighter = "custom_flakefighter:CustomFlakefighter"

Of course, for this to work, your module needs to be discoverable on your python path.
That is, you should be able to execute :code:`from custom_flakefighter import CustomFlakefighter` successfully from within the same directory as where you are running :code:`pytest`.
You can then configure it just like any other flakefighter.

..  code-block:: ini

  [tool.pytest.ini_options.pytest_flakefighters.flakefighters.custom_flakefighter.CustomFlakefighter]
  run_live=true
  custom_arg=0.1
