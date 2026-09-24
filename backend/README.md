# Backend RescueSync

API principal de RescueSync construida con FastAPI, SQLModel y Alembic.

## Stack

- Python 3.12
- FastAPI
- Uvicorn
- SQLModel
- Alembic
- PostgreSQL

## Puertos y endpoints

- API: `http://localhost:3000`
- Swagger UI: `http://localhost:3000/docs`
- Healthcheck: `http://localhost:3000/health`
- Prefijo actual de la API: `/api/rescue`

## Requisitos

- Docker Desktop en ejecución
- `docker compose` disponible

## Variables de entorno

El servicio usa estas variables definidas en `docker-compose.yml`:

- `HOST=0.0.0.0`
- `PORT=3000`
- `DATABASE_URL=postgresql://bonita:bpm@bonita-db:5432/rescuesync`

Alembic y la conexión de SQLModel dependen de `DATABASE_URL`. Si la variable no existe, el backend falla al iniciar.

## Levantar el backend

Para levantar la infraestructura del proyecto:

```bash
docker compose up -d
```

Si querés reconstruir la imagen:

```bash
docker compose up -d --build backend
```

Si además modificaste dependencias y querés forzar una reconstrucción completa sin reutilizar capas previas:

```bash
docker compose build --no-cache backend
docker compose up -d backend
```

Para seguir los logs del servicio:

```bash
docker compose logs -f backend
```

## Cómo arranca el contenedor

El contenedor del backend ejecuta `start.sh` y hace este flujo:

1. Corre `alembic upgrade head`
2. Si la migración falla, el contenedor se detiene
3. Si todo sale bien, inicia Uvicorn en el puerto `3000`

Esto evita arrancar la API con un esquema desactualizado.

## Flujo de migraciones con Alembic

Con la infraestructura levantada, el flujo es siempre el mismo:

```bash
docker compose exec backend alembic revision --autogenerate -m "descripcion breve del cambio"
docker compose exec backend alembic upgrade head
```

El texto entre comillas es solo un mensaje descriptivo de la migración. Por ejemplo: `crear tabla emergencias`, `agregar campo estado` o cualquier descripción breve del cambio de esquema.

El primer comando genera un archivo nuevo en `backend/alembic/versions/`. Antes de aplicarlo o subirlo a Git, revisalo porque Alembic lo genera como una migración candidata.

Chequeá al menos esto:

- Que el `upgrade()` haga exactamente el cambio esperado
- Que el `downgrade()` revierta ese cambio
- Que tipos, `nullable`, defaults y claves queden correctos

Como `start.sh` ya ejecuta `alembic upgrade head`, el contenedor intenta mantener el esquema actualizado cada vez que inicia.

## Estructura relevante

```text
backend/
├── main.py                # aplicación FastAPI
├── database.py            # engine y sesiones
├── start.sh               # corre migraciones e inicia uvicorn
├── models/                # modelos SQLModel
├── routers/               # rutas FastAPI
├── alembic.ini            # configuración Alembic
└── alembic/
    ├── env.py             # integra Alembic con SQLModel
    └── versions/          # migraciones generadas
```

## Comandos útiles

Abrir una shell dentro del contenedor:

```bash
docker compose exec backend sh
```

Ver el historial de migraciones:

```bash
docker compose exec backend alembic history
```

Ver la revisión actual aplicada en la base:

```bash
docker compose exec backend alembic current
```

## Subir cambios a Git

Después de generar y revisar la migración, subí a Git:

- El archivo nuevo dentro de `backend/alembic/versions/`
- Los cambios del modelo, si existieron
- Este README del backend, si aplica

No conviene generar migraciones en forma manual fuera de Alembic si el cambio proviene de modelos ya versionados.