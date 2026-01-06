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
    """

    id: Mapped[int] = Column(Integer, primary_key=True)  # pylint: disable=C0103
    # @pytest, these are not the tests you're looking for...
    __test__ = False  # pylint: disable=C0103

    @declared_attr
    def __tablename__(self):
        return self.__name__.lower()


@dataclass
class Run(Base):
    """
    Class to store attributes of a flakefighters run.
    """

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
    """

    run_id: Mapped[int] = Column(Integer, ForeignKey("run.id"), nullable=False)
    name: Mapped[str] = Column(String)
    params: Mapped[dict] = Column(PickleType)


@dataclass
class Test(Base):
    """
    Class to store attributes of a test case.
    """

    run_id: Mapped[int] = Column(Integer, ForeignKey("run.id"), nullable=False)
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
    """

    __tablename__ = "flakefighter_result"

    test_execution_id: Mapped[int] = Column(Integer, ForeignKey("test_execution.id"), nullable=True)
    test_id: Mapped[int] = Column(Integer, ForeignKey("test.id"), nullable=True)
    name: Mapped[str] = Column(String)
    flaky: Mapped[bool] = Column(Boolean)

    __table_args__ = (
        CheckConstraint("NOT (test_execution_id IS NULL AND test_id IS NULL)", name="check_test_id_not_null"),
    )


class Database:
    """
    Class to handle database setup and interaction.
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
            return session.scalars(select(Run).order_by(desc(Run.id)).limit(limit)).all()
