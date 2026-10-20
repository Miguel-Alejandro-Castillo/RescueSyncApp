#!/bin/sh
set -eu

SETUP_DIR="/opt/bonita/setup"
TENANT_ID="${BONITA_TENANT_ID:-1}"
case "$TENANT_ID" in
    ''|*[!0-9]*) echo "BONITA_TENANT_ID debe ser numérico" >&2; exit 1 ;;
esac

cd "$SETUP_DIR"
./setup.sh pull
PERMISSIONS_FILE="platform_conf/current/tenants/$TENANT_ID/tenant_portal/custom-permissions-mapping.properties"
[ -f "$PERMISSIONS_FILE" ] || { echo "No existe la configuración del tenant $TENANT_ID" >&2; exit 1; }

TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT HUP INT TERM
awk '
    BEGIN { key = "user|bonita.bpm"; permission = "organization_visualization" }
    index($0, key "=") == 1 {
        found = 1
        if (index($0, permission) == 0) {
            if ($0 ~ /\[\]/) sub(/\[\]/, "[" permission "]")
            else sub(/\][[:space:]]*$/, "," permission "]")
        }
        print
        next
    }
    { print }
    END { if (!found) print key "=[" permission "]" }
' "$PERMISSIONS_FILE" > "$TEMP_FILE"

if cmp -s "$PERMISSIONS_FILE" "$TEMP_FILE"; then
    echo "Permiso de lectura de organización de bonita.bpm ya configurado."
    exit 0
fi

cp "$PERMISSIONS_FILE" "$PERMISSIONS_FILE.before-integration-permissions"
cat "$TEMP_FILE" > "$PERMISSIONS_FILE"
./setup.sh push
echo "Permiso organization_visualization asignado solo a bonita.bpm. Reiniciar Bonita para aplicarlo."
