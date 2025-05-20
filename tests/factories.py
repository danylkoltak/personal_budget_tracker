import pytest
from src.models import User

@pytest.fixture
def test_user(db_session):
    user = User(username="test", password="hashed")
    db_session.add(user)
    db_session.commit()
    return user