import os

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlmodel import Session, SQLModel, create_engine

from database import get_session
from dependencies.bonita import get_bonita_service
from dependencies.jwt_auth import ALGORITHM, SECRET_KEY
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


class BonitaFalso:
    async def obtener_proceso_por_nombre(self, process_name):
        return {"id": "1"}

    async def iniciar_proceso(self, process_id, contract=None):
        return {"caseId": "1001"}

    async def esperar_tarea_humana_por_caso(self, case_id, *args, **kwargs):
        return {"id": "1"}

    async def completar_tarea_humana(self, task_id, contract=None):
        return None

    async def borrar_caso_por_id(self, case_id):
        return None


async def get_bonita_falso():
    yield BonitaFalso()


def crear_token(rol: str) -> str:
    payload = {
        "sub": f"test_{rol}",
        "user_id": "1",
        "memberships": [{
            "group": {"name": "test", "displayName": "Test"},
            "role": {"name": rol, "displayName": rol},
        }],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture
def auth_headers():
    def _headers(rol: str) -> dict:
        return {"Authorization": f"Bearer {crear_token(rol)}"}
    return _headers


@pytest.fixture(name="client")
def client_fixture():
    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_bonita_service] = get_bonita_falso

    yield TestClient(app)

    app.dependency_overrides.clear()

@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session
