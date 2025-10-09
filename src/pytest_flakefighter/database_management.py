"""
This module manages all interaction with the test run database.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    PickleType,
    String,
    Text,
    create_engine,
    desc,
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
    junit_xml: Mapped[str] = Column(Text)
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

    def __init__(self, url: str, max_runs: int = None, time_immemorial: datetime = None):
        self.engine = create_engine(url)
        Base.metadata.create_all(self.engine)

    def save(self, run: Run):
        """
        Save the given run into the database.
        """
        with Session(self.engine) as session:
            session.add(run)
            session.commit()
            session.flush()

    def load_runs(self, limit: int = None):
        """
        Load runs from the database.

        :param limit: The maximum number of runs to return (these will be most recent runs).
        """
        with Session(self.engine) as session:
            return session.scalars(select(Run).order_by(desc(Run.id)).limit(limit)).all()
