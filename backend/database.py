import os

from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine

# Obtiene la URL de la base de datos desde la variable de entorno DATABASE_URL
DATABASE_URL = os.getenv(
"DATABASE_URL"
)

if not DATABASE_URL:
    raise RuntimeError(
        "La variable de entorno DATABASE_URL no está configurada"
    )

engine = create_engine(
    DATABASE_URL,
    echo=True
)

# Que se encargue alembic de la creación de las tablas
#def create_db():
#    SQLModel.metadata.create_all(
#        engine
#    )
#

def get_session():

    with Session(engine) as session:
        yield session