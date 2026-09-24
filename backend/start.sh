#!/bin/sh

# set -e detiene el contenedor si falla una migración. Así evitás que FastAPI arranque con un esquema desactualizado.
set -e

echo "Aplicando migraciones de Alembic..."
alembic upgrade head

echo "Iniciando RescueSync Backend..."
# exec permite que Uvicorn reciba correctamente las señales de Docker.
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 3000 \
    --reload