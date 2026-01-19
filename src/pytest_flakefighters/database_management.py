"""
This module manages all interaction with the test run database.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Union

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    PickleType,
    String,
    Text,
    create_engine,
    desc,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    declared_attr,
    relationship,
)


@dataclass
class Base(DeclarativeBase):
    """
    Declarative base class for data objects.

    :ivar id: Unique autoincrementing ID for the object.
    """

    id: Mapped[int] = Column(Integer, primary_key=True)  # pylint: disable=C0103
    # Explicitly flag that we don't want pytest to collect our Test, TestExecution, etc. classes.
    __test__ = False  # pylint: disable=C0103

    @declared_attr
    def __tablename__(self):
        return self.__name__.lower()


@dataclass
class Run(Base):
    """
    Class to store attributes of a flakefighters run.
    :ivar start_time: The time the test run was begun.
    :ivar created_at: The time the entry was added to the database.
    This is not necessarily equivalent to start_time if the test suite took a long time to run or
    if the entry was migrated from a separate database.
    :ivar root: The root directory of the project.
    :ivar tests: The test suite.
    :ivar active_flakefighters: The flakefighters that are active on the run.
    """

    start_time = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    root: Mapped[str] = Column(String)
    tests = relationship("Test", backref="run", lazy="subquery", cascade="all, delete", passive_deletes=True)
    active_flakefighters = relationship(
        "ActiveFlakeFighter", backref="run", lazy="subquery", cascade="all, delete", passive_deletes=True
    )


@dataclass
class ActiveFlakeFighter(Base):
    """
    Store relevant information about the active flakefighters.

    :ivar run_id: Foreign key of the related run.
    :ivar name: Class name of the flakefighter.
    :ivar params: The parameterss of the flakefighter.
    """

    run_id: Mapped[int] = Column(Integer, ForeignKey("run.id"), nullable=False)
    name: Mapped[str] = Column(String)
    params: Mapped[dict] = Column(PickleType)


@dataclass
class Test(Base):
    """
    Class to store attributes of a test case.

    :ivar run_id: Foreign key of the related run.
    :ivar fspath: File system path of the file containing the test definition.
    :ivar line_no: Line number of the test definition.
    :ivar name: Name of the test case.
    :ivar skipped: Boolean true if the test was skipped, else false.
    :ivar executions: List of execution attempts.
    :ivar flakefighter_results: List of test-level flakefighter results.

    .. note::
      Execution-level flakefighter results will be stored inside the individual TestExecution objects
    """

    run_id: Mapped[int] = Column(Integer, ForeignKey("run.id"), nullable=False)
    fspath: Mapped[str] = Column(String)
    line_no: Mapped[int] = Column(Integer)
    name: Mapped[str] = Column(String)
    skipped: Mapped[bool] = Column(Boolean, default=False)
    executions = relationship(
        "TestExecution", backref="test", lazy="subquery", cascade="all, delete", passive_deletes=True
    )
    flakefighter_results = relationship(
        "FlakefighterResult", backref="test", lazy="subquery", cascade="all, delete", passive_deletes=True
    )

    @property
    def flaky(self) -> bool:
        """
        Return whether a test (or any of its executions) has been marked as flaky by any flakefighter.
        """
        if not self.executions and not self.flakefighter_results:
            return None
        return any(result.flaky for result in self.flakefighter_results) or any(
            execution.flaky for execution in self.executions
        )


@dataclass
class TestExecution(Base):  # pylint: disable=R0902
    """
    Class to store attributes of a test outcome.

    :ivar test_id: Foreign key of the related test.
    :ivar outcome: Outcome of the test. One of "passed", "failed", or "skipped".
    :ivar stdout: The captured stdout string.
    :ivar stedrr: The captured stderr string.
    :ivar start_time: The start time of the test.
    :ivar end_time: The end time of the test.
    :ivar coverage: The line coverage of the test.
    :ivar flakefighter_results: The execution-level flakefighter results.
    :ivar exception: The exception associated with the test if one was thrown.
    """

    __tablename__ = "test_execution"

    test_id: Mapped[int] = Column(Integer, ForeignKey("test.id"), nullable=False)
    outcome: Mapped[str] = Column(String)
    stdout: Mapped[str] = Column(Text)
    stderr: Mapped[str] = Column(Text)
    report: Mapped[str] = Column(Text)
    start_time: Mapped[datetime] = Column(DateTime(timezone=True))
    end_time: Mapped[datetime] = Column(DateTime(timezone=True))
    coverage: Mapped[dict] = Column(PickleType)
    flakefighter_results = relationship(
        "FlakefighterResult", backref="test_execution", lazy="subquery", cascade="all, delete", passive_deletes=True
    )
    exception = relationship(
        "TestException",
        uselist=False,
        backref="test_execution",
        lazy="subquery",
        cascade="all, delete",
        passive_deletes=True,
    )

    @property
    def flaky(self) -> bool:
        """
        Return whether a test (or any of its executions) has been marked as flaky by any flakefighter.
        """
        return any(result.flaky for result in self.flakefighter_results)


@dataclass
class TestException(Base):  # pylint: disable=R0902
    """
    Class to store information about the exceptions that cause tests to fail.

    :ivar execution_id: Foreign key of the related execution.
    :ivar name: Name of the exception.
    :traceback: The full stack of traceback entries.
    """

    __tablename__ = "test_exception"

    execution_id: Mapped[int] = Column(Integer, ForeignKey("test_execution.id"), nullable=False)
    name: Mapped[str] = Column(String)
    traceback = relationship(
        "TracebackEntry", backref="exception", lazy="subquery", cascade="all, delete", passive_deletes=True
    )


@dataclass
class TracebackEntry(Base):  # pylint: disable=R0902
    """
    Class to store attributes of entries in the stack trace.

    :ivar exception_id: Foreign key of the related exception.
    :ivar path: Filepath of the source file.
    :ivar lineno: Line number of the executed statement.
    :ivar colno: Column number of the executed statement.
    :ivar statement: The executed statement.
    :ivar source: The surrounding source code.
    """

    exception_id: Mapped[int] = Column(Integer, ForeignKey("test_exception.id"), nullable=False)
    path: Mapped[str] = Column(String)
    lineno: Mapped[int] = Column(Integer)
    colno: Mapped[int] = Column(Integer)
    statement: Mapped[str] = Column(String)
    source: Mapped[str] = Column(Text)


@dataclass
class FlakefighterResult(Base):  # pylint: disable=R0902
    """
    Class to store flakefighter results.

    :ivar test_execution_id: Foreign key of the related test execution. Should not be set if test_id is present.
    :ivar test_id: Foreign key of the related test. Should not be set if test_execution_id is present.
    :ivar name: Name of the flakefighter.
    :ivar flaky: Boolean true if the test (execution) was classified as flaky.
    """

    __tablename__ = "flakefighter_result"

    test_execution_id: Mapped[int] = Column(Integer, ForeignKey("test_execution.id"), nullable=True)
    test_id: Mapped[int] = Column(Integer, ForeignKey("test.id"), nullable=True)
    name: Mapped[str] = Column(String)
    flaky: Mapped[bool] = Column(Boolean)

    __table_args__ = (
        CheckConstraint("(test_execution_id IS NOT NULL) + (test_id IS NOT NULL) = 1", name="check_test_id_not_null"),
    )

    @property
    def classification(self):
        """
        Return the classification as a string.
        "flaky" if the test was classified as flaky, else "genuine".
        """
        return "flaky" if self.flaky else "genuine"

    def to_dict(self):
        """
        Return the name and classification as a dictionary.
        """
        return {"name": self.name, "classification": self.classification}


class Database:
    """
    Class to handle database setup and interaction.

    :ivar engine: The database engine.
    :ivar store_max_runs: The maximum number of previous runs that should be stored. If the database exceeds this size,
                          older runs will be pruned to make space for newer ones.
    :ivar time_immemorial: Time before which runs should not be considered. Runs before this date will be pruned when
                           saving new runs.
    :ivar previous_runs: List of previous flakefighter runs with most recent first.
    """

    def __init__(
        self,
        url: str,
        load_max_runs: int = None,
        store_max_runs: int = None,
        time_immemorial: Union[timedelta, str] = None,
    ):
        if isinstance(time_immemorial, str) and time_immemorial:
            days, hours, minutes = [int(x) for x in time_immemorial.split(":")]
            time_immemorial = timedelta(days=days, hours=hours, minutes=minutes)

        self.engine = create_engine(url)
        Base.metadata.create_all(self.engine)

        self.store_max_runs = store_max_runs
        self.time_immemorial = time_immemorial
        self.previous_runs = self.load_runs(load_max_runs)

    def save(self, run: Run):
        """
        Save the given run into the database.
        """
        with Session(self.engine) as session:
            session.add(run)
            if self.time_immemorial is not None:
                expiry_date = datetime.now() - self.time_immemorial
                for r in session.query(Run).filter(Run.created_at < (expiry_date - self.time_immemorial)):
                    session.delete(r)

            if self.store_max_runs is not None:
                for r in self.load_runs()[self.store_max_runs - 1 :]:
                    session.delete(r)
            session.commit()
            session.flush()

    def load_runs(self, limit: int = None):
        """
        Load runs from the database.

        :param limit: The maximum number of runs to return (these will be most recent runs).
        """
        with Session(self.engine) as session:
            return session.scalars(select(Run).order_by(desc(Run.start_time)).limit(limit)).all()
