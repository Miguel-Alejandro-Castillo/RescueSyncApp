#!/usr/bin/env sh
set -eu

# Evita que Git Bash (MINGW) convierta rutas tipo /opt/... en C:/Program Files/Git/opt/...
export MSYS_NO_PATHCONV=1

wait_for_health() {
  service="$1"
  timeout="${2:-180}"
  elapsed=0
  echo "Esperando a que '$service' esté listo..."
  while [ "$elapsed" -lt "$timeout" ]; do
    cid=$(docker compose ps -q "$service" 2>/dev/null || true)
    if [ -n "$cid" ]; then
      health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)
      if [ "$health" = "healthy" ] || [ "$health" = "running" ]; then
        echo "  '$service' listo."
        return 0
      fi
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done
  echo "ERROR: Timeout esperando a '$service'."
  exit 1
}

echo "=== 1/5 Eliminando contenedores y volúmenes ==="
docker compose down -v

echo ""
echo "=== 2/5 Levantando contenedores ==="
docker compose up -d

wait_for_health bonita-db 180
wait_for_health nacional-db 180
wait_for_health bonita-engine 240
wait_for_health nacional 180
wait_for_health backend 180

echo ""
echo "=== 3/5 Desplegando organización, proceso y permisos en Bonita ==="
docker compose exec -T bonita-engine sh /opt/bonita/deploy.sh
docker compose exec -T bonita-engine sh /opt/bonita/configure-platform.sh

echo ""
echo "=== 4/5 Ejecutando seeds de API Nacional ==="
docker compose exec -T nacional npx prisma generate
docker compose exec -T nacional npx prisma db seed

echo ""
echo "=== 5/5 Ejecutando seeds de Backend ==="
docker compose exec -T backend python seed_casos_finalizados.py
docker compose exec -T backend python seed_escenarios.py

echo ""
echo "Listo. La aplicación quedó inicializada y lista para usar."
