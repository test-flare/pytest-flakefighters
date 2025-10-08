"""
This module manages all interaction with the test run database.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
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
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, relationship

if os.path.exists(".env"):
    load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///flakefighter.db")
engine = create_engine(DATABASE_URL)


class Base(DeclarativeBase):
    def save(self):
        """
        Save the current run into the database.
        """
        with Session(engine) as session:
            session.add(self)
            session.commit()
            session.flush()


@dataclass
class Run(Base):
    """
    Class to store attributes of a flakefighter run.
    """

    __tablename__ = "runs"  # pylint: disable=C0103
    id: Mapped[int] = Column(Integer, primary_key=True)
    source_commit: Mapped[str] = Column(String)
    target_commit: Mapped[str] = Column(String)
    junit_xml: Mapped[str] = Column(Text)
    tests = relationship("Test", back_populates="run", lazy="subquery")

    def __repr__(self) -> str:
        return f"Run(id={self.id}, source_commit={self.source_commit}, target_commit={self.target_commit})"


@dataclass
class Test(Base):
    """
    Class to store attributes of a test execution.
    """

    __tablename__ = "tests"
    id: Mapped[int] = Column(Integer, primary_key=True)
    run_id: Mapped[int] = Column(Integer, ForeignKey("runs.id"), nullable=False)
    name: Mapped[str] = Column(String)
    outcome: Mapped[str] = Column(String)  # pylint: disable=C0103
    stdout: Mapped[str] = Column(Text)
    stderr: Mapped[str] = Column(Text)
    start_time: Mapped[int] = Column(DateTime(timezone=True))
    end_time: Mapped[int] = Column(DateTime(timezone=True))
    coverage: Mapped[dict] = Column(PickleType)
    run = relationship("Run", back_populates="tests", lazy="subquery")


Base.metadata.create_all(engine)


def load_runs(limit: int = None):
    """
    Load runs from the database.

    :param limit: The maximum number of runs to return (these will be most recent runs).
    """
    with Session(engine) as session:
        return session.scalars(select(Run).order_by(desc(Run.id)).limit(limit)).all()
