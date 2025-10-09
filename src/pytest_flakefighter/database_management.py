"""
This module manages all interaction with the test run database.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Union

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    PickleType,
    String,
    Text,
    asc,
    create_engine,
    delete,
    desc,
    func,
    select,
)
from sqlalchemy.orm import Mapped, Session, declarative_base, relationship

Base = declarative_base()


@dataclass
class Run(Base):
    """
    Class to store attributes of a flakefighter run.
    """

    __tablename__ = "runs"  # pylint: disable=C0103
    id: Mapped[int] = Column(Integer, primary_key=True)  # pylint: disable=C0103
    source_commit: Mapped[str] = Column(String)
    target_commit: Mapped[str] = Column(String)
    created_at = Column(DateTime, default=func.now())
    tests = relationship("Test", back_populates="run", lazy="subquery")


@dataclass
class Test(Base):  # pylint: disable=R0902
    """
    Class to store attributes of a test execution.
    """

    __tablename__ = "tests"  # pylint: disable=C0103
    id: Mapped[int] = Column(Integer, primary_key=True)  # pylint: disable=C0103
    run_id: Mapped[int] = Column(Integer, ForeignKey("runs.id"), nullable=False)
    name: Mapped[str] = Column(String)
    outcome: Mapped[str] = Column(String)
    stdout: Mapped[str] = Column(Text)
    stderr: Mapped[str] = Column(Text)
    start_time: Mapped[datetime] = Column(DateTime(timezone=True))
    end_time: Mapped[datetime] = Column(DateTime(timezone=True))
    coverage: Mapped[dict] = Column(PickleType)
    run = relationship("Run", back_populates="tests", lazy="subquery")


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
                session.query(Run).filter(Run.created_at < (expiry_date - self.time_immemorial)).delete()
            if self.max_runs is not None:
                to_delete = [run.id for run in self.load_runs()][self.max_runs - 1 :]
                session.query(Run).filter(Run.id.in_(to_delete)).delete()
            session.commit()
            session.flush()

    def load_runs(self, limit: int = None):
        """
        Load runs from the database.

        :param limit: The maximum number of runs to return (these will be most recent runs).
        """
        with Session(self.engine) as session:
            return session.scalars(select(Run).order_by(desc(Run.id)).limit(limit)).all()
