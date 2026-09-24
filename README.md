# RescueSyncApp

Guia rapida para ejecutar la infraestructura con Docker Compose.

## Requisitos

- Docker Desktop en ejecucion
- `docker compose` disponible en la terminal

## Levantar toda la infraestructura

El comando principal para levantar toda la infraestructura es:

```bash
docker compose up -d
```

Usa ese comando al inicio cuando los servicios ya fueron construidos y solo necesitas poner en marcha todo el stack.

Si ademas quieres reconstruir las imagenes mientras levantas todo, ejecuta:

```bash
docker compose up -d --build
```

Si necesitas forzar una reconstruccion completa sin usar la cache de Docker y volver a ejecutar todo el `Dockerfile`, ejecuta:

```bash
docker compose build --no-cache
docker compose up -d
```

Si quieres hacerlo solo para un servicio en particular, por ejemplo `backend`:

```bash
docker compose build --no-cache backend
docker compose up -d backend
```

Esto levanta y construye estos servicios:

- `bonita-db`
- `bonita-engine`
- `backend`
- `frontend`

## URLs publicadas

Una vez levantada toda la infraestructura, podras acceder a:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:3000`
- Swagger del backend: `http://localhost:3000/docs`
- Nacional: `http://localhost:4000`
- Swagger de la api Nacional: `http://localhost:4000/api-docs/`

## Actualizar solo el backend

Si hiciste cambios en `backend/` y quieres reconstruir solo ese servicio:

```bash
docker compose up -d --build backend
```

Si no necesitas reconstruir la imagen y solo quieres reiniciarlo:

```bash
docker compose restart backend
```

## Actualizar solo el frontend

Si hiciste cambios en `frontend/` y quieres reconstruir solo ese servicio:

```bash
docker compose up -d --build frontend
```

Si no necesitas reconstruir la imagen y solo quieres reiniciarlo:

```bash
docker compose restart frontend
```

## Ver estado de los contenedores

```bash
docker compose ps
```

## Ver logs

Logs de todos los servicios:

```bash
docker compose logs -f
```

Logs solo del backend:

```bash
docker compose logs -f backend
```

Logs solo del frontend:

```bash
docker compose logs -f frontend
```

## Detener sin eliminar

Si solo quieres detener los contenedores, sin eliminar la infraestructura creada por Compose:

```bash
docker compose stop
```

## Eliminar toda la infraestructura

`docker compose down` no solo detiene los contenedores: tambien elimina la infraestructura creada por Compose, como la red y los contenedores del proyecto.

```bash
docker compose down
```

Si tambien quieres eliminar los volumenes creados:

```bash
docker compose down -v
```

## Para correr los tests de integracion
```bash
docker compose exec backend python -m pytest tests/ -v
```
## Para correr un test de integracion en particular
```bash
docker compose exec backend python -m pytest tests/tu-test.py
```
