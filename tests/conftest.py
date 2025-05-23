import os
import pytest
import sqlalchemy
from sqlalchemy_utils import database_exists, create_database, drop_database
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from src.database import Base, get_db
from main import app  # Adjust path if necessary
from fastapi.testclient import TestClient

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

from urllib.parse import urlparse

parsed_url = urlparse(DATABASE_URL)
username = parsed_url.username or "budget"
password = parsed_url.password or "budget123"
hostname = parsed_url.hostname or "localhost"
port = parsed_url.port or 5432

TEST_DB_NAME = "budget_test_db"
POSTGRES_ADMIN_URL = f"postgresql://{username}:{password}@{hostname}:{port}/postgres"
TEST_DB_URL = f"postgresql://{username}:{password}@{hostname}:{port}/{TEST_DB_NAME}"

engine = sqlalchemy.create_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create and drop the test DB around the test session."""
    if database_exists(TEST_DB_URL):
        drop_database(TEST_DB_URL)

    create_database(TEST_DB_URL)

    Base.metadata.create_all(bind=engine)
    yield
    drop_database(TEST_DB_URL)


@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c