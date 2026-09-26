import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from database import get_session
from main import app
from services.bonita_service import BonitaService

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


@pytest.fixture(autouse=True)
def bonita_falso(monkeypatch):
    async def login(self, username, password):
        return {"success": True}

    async def obtener_procesos_por_nombre(self, process_name):
        return [{"id": "1"}]

    async def iniciar_proceso(self, process_id, contract={}):
        return {}

    monkeypatch.setattr(BonitaService, "login", login)
    monkeypatch.setattr(BonitaService, "obtener_procesos_por_nombre", obtener_procesos_por_nombre)
    monkeypatch.setattr(BonitaService, "iniciar_proceso", iniciar_proceso)


@pytest.fixture(name="client")
def client_fixture():
    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override

    yield TestClient(app)

    app.dependency_overrides.clear()

@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session
