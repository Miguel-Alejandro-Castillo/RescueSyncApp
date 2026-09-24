import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from database import get_session
from main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://bonita:bpm@bonita-db:5432/rescuesync_test",
)

engine = create_engine(TEST_DATABASE_URL)


@pytest.fixture(autouse=True)
def crear_tablas():
    SQLModel.metadata.create_all(engine)

    yield

    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture():
    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override

    yield TestClient(app)

    app.dependency_overrides.clear()


# Sesión independiente de la del endpoint: solo ve datos ya commiteados.
@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session
