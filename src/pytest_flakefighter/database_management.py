"""
This module manages all interaction with the test run database.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Union

from sqlalchemy import (
    Boolean,
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

    @declared_attr
    def __tablename__(self):
        return self.__name__.lower()


@dataclass
class Run(Base):
    """
    Class to store attributes of a flakefighter run.
    """

    source_commit: Mapped[str] = Column(String)
    target_commit: Mapped[str] = Column(String)
    created_at = Column(DateTime, default=func.now())
    tests = relationship("Test", backref="run", lazy="subquery", cascade="all, delete", passive_deletes=True)


@dataclass
class Test(Base):  # pylint: disable=R0902
    """
    Class to store attributes of a test case.
    """

    run_id: Mapped[int] = Column(Integer, ForeignKey("run.id"), nullable=False)
    name: Mapped[str] = Column(String)
    flaky: Mapped[bool] = Column(Boolean)
    skipped: Mapped[bool] = Column(Boolean, default=False)
    executions = relationship(
        "TestExecution", backref="test", lazy="subquery", cascade="all, delete", passive_deletes=True
    )


@dataclass
class TestExecution(Base):  # pylint: disable=R0902
    """
    Class to store attributes of a test outcome.
    """

    test_id: Mapped[int] = Column(Integer, ForeignKey("test.id"), nullable=False)
    outcome: Mapped[str] = Column(String)
    stdout: Mapped[str] = Column(Text)
    stderr: Mapped[str] = Column(Text)
    stack_trace: Mapped[str] = Column(Text)
    start_time: Mapped[datetime] = Column(DateTime(timezone=True))
    end_time: Mapped[datetime] = Column(DateTime(timezone=True))
    coverage: Mapped[dict] = Column(PickleType)


class Database:
    """
    Class to handle database setup and interaction.
    """

    def __init__(self, url: str, max_runs: int = None, time_immemorial: Union[timedelta, str] = None):
        if isinstance(time_immemorial, str) and time_immemorial:
            days, hours, minutes = [int(x) for x in time_immemorial.split(":")]
            time_immemorial = timedelta(days=days, hours=hours, minutes=minutes)

        self.engine = create_engine(url)
        self.max_runs = max_runs
        self.time_immemorial = time_immemorial
        Base.metadata.create_all(self.engine)

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

            if self.max_runs is not None:
                for r in self.load_runs()[self.max_runs - 1 :]:
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
