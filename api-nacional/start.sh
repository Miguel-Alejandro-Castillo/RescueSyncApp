#!/bin/sh

# set -e detiene el contenedor si falla una migración. Así evitás que la API Nacional arranque con un esquema desactualizado.
set -e

echo "Aplicando migraciones de Prisma..."
npx prisma migrate deploy

echo "Iniciando la API Nacional..."
npm run dev