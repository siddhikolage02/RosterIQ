
import pytest

from tests.test_database import (
    create_test_database,
    drop_test_database,
    get_test_db,
)


@pytest.fixture()
def db():
    drop_test_database()
    create_test_database()

    session = get_test_db()

    try:
        yield session
    finally:
        session.close()
        drop_test_database()
