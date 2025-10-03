"""
This module manages all interaction with the test run database.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Integer,
    Mapped,
    String,
    Text,
    create_engine,
    desc,
    select,
)
from sqlalchemy.orm import Session, declarative_base

if os.path.exists(".env"):
    load_dotenv()

Base = declarative_base()
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///flakefighter.db")
engine = create_engine(DATABASE_URL)


@dataclass
class Run(Base):
    """
    Class to store attributes of a flakefighter run.
    """

    __tablename__ = "runs"  # pylint: disable=C0103
    id: Mapped[int] = Column(Integer, primary_key=True)
    timestamp: Mapped[int] = Column(Integer)
    source_commit: Mapped[str] = Column(String)
    target_commit: Mapped[str] = Column(String)
    junit_xml: Mapped[str] = Column(Text)

    def __repr__(self) -> str:
        return (
            f"Run(id={self.id}, timestamp={self.timestamp}, source_commit={self.source_commit},"
            f"target_commit={self.target_commit})"
        )

    def save(self):
        """
        Save the current run into the database.
        """
        with Session(engine) as session:
            session.add(self)
            session.commit()
            session.flush()


Base.metadata.create_all(engine)


def load_runs(limit: int = None):
    """
    Load runs from the database.

    :param limit: The maximum number of runs to return (these will be most recent runs).
    """
    with Session(engine) as session:
        return session.scalars(select(Run).order_by(desc(Run.id)).limit(limit)).all()
