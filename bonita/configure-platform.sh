#!/bin/sh

set -eu

BONITA_SETUP_DIR="/opt/bonita/setup"
ARTIFACTS_DIR="/opt/bonita/artifacts"

CUSTOM_PERMISSIONS_SOURCE="$ARTIFACTS_DIR/custom-permissions-mapping.properties"

echo "==================================="
echo "Bonita Platform Configuration"
echo "==================================="

if [ ! -f "$CUSTOM_PERMISSIONS_SOURCE" ]; then
    echo "ERROR: no existe:"
    echo "$CUSTOM_PERMISSIONS_SOURCE"
    exit 1
fi

cd "$BONITA_SETUP_DIR"

echo ""
echo "Realizando pull de la configuración actual..."

./setup.sh pull

TARGET=$(
    find platform_conf/current/tenants \
        -type f \
        -name 'custom-permissions-mapping.properties' \
        -print -quit
)

if [ -z "$TARGET" ]; then
    echo "ERROR: no se encontró custom-permissions-mapping.properties"
    exit 1
fi

echo "Archivo encontrado:"
echo "$TARGET"

echo ""
echo "Aplicando configuración personalizada..."

cp "$CUSTOM_PERMISSIONS_SOURCE" "$TARGET"

echo ""
echo "Realizando push de la configuración..."

./setup.sh push

echo ""
echo "==================================="
echo "Configuración actualizada"
echo "==================================="