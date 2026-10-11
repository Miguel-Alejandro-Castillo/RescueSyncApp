
# Prisma & Migraciones de Base de Datos

Guía esencial para trabajar con Prisma en Docker Compose.

## Estructura del Schema

El schema de Prisma se define en `prisma/schema.prisma`.
Por ejemplo:
```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  name  String?
  posts Post[]
}

model Post {
  id        Int     @id @default(autoincrement())
  title     String
  content   String?
  published Boolean @default(false)
  author    User    @relation(fields: [authorId], references: [id])
  authorId  Int
}
```

## Comandos Esenciales con Docker Compose

### Generar Prisma Client (Automático)

Se ejecuta automáticamente cuando se crea la imagen Docker:

```bash
docker compose exec nacional npx prisma generate
```

### Crear una Nueva Migración

Después de modificar `prisma/schema.prisma`:

```bash
docker compose exec nacional npx prisma migrate dev --name <nombre_migracion>
```

Este comando crea la migración, la aplica y regenera automáticamente Prisma Client.

### Ver Estado de Migraciones

```bash
docker compose exec nacional npx prisma migrate status
```

Muy útil para verificar qué migraciones se han aplicado.

### Aplicar Migraciones Pendientes (Automático)

Se ejecuta automáticamente en `start.sh` en cada inicio del contenedor:

```bash
npx prisma migrate deploy
```

### Cargar Datos Iniciales con Seed

Ejecuta el archivo `prisma/seed.js` para cargar datos iniciales:

```bash
docker compose exec nacional npx prisma db seed
```

### Abrir Prisma Studio (GUI Prisma)

Herramienta visual para inspeccionar y manipular datos sin necesidad de cliente de base de datos:

```bash
docker compose exec nacional npx prisma studio
```

Luego accede a `http://localhost:5555`

### Resetear Base de Datos (Solo Desarrollo)

```bash
docker compose exec nacional npx prisma migrate reset
```

Resetea toda la base de datos, ideal solo para desarrollo. Reaplica todas las migraciones y ejecuta el seed.

## Workflow Típico

1. **Modificar schema**: Edita `prisma/schema.prisma`
2. **Crear migración**: `docker compose exec api npx prisma migrate dev --name descripcion`
3. **Verificar cambios**: Usa Prisma Studio o consulta directamente
4. **Producción**: `docker compose exec api npx prisma migrate deploy`

## Notas Importantes

- Las migraciones se aplican automáticamente en desarrollo
- En producción, usa `prisma migrate deploy` antes de iniciar la app
- Nunca commitees `.env` con credenciales reales
- Los archivos de migración van en `prisma/migrations/`
