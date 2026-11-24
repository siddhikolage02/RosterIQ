
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import Base
from src.database import models


TEST_DATABASE_PATH = (
    Path(__file__).parent / "data" / "rosteriq_test.db"
)

TEST_DATABASE_URL = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def create_test_database():
    TEST_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=test_engine)


def drop_test_database():
    Base.metadata.drop_all(bind=test_engine)


def get_test_db():
    return TestingSessionLocal()
