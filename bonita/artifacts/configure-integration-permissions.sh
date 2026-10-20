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
awk -v backend_user="${BONITA_USER:-walter.bates}" '
    BEGIN { permissions["user|bonita.bpm"] = "organization_visualization"; permissions["user|" backend_user] = "read_sistema_nacional" }
    { key = $0; sub(/=.*/, "", key); permission = permissions[key] }
    permission != "" {
        found[key] = 1
        if (index($0, permission) == 0) {
            if ($0 ~ /\[\]/) sub(/\[\]/, "[" permission "]")
            else sub(/\][[:space:]]*$/, "," permission "]")
        }
        print
        next
    }
    { print }
    END { for (key in permissions) if (!found[key]) print key "=[" permissions[key] "]" }
' "$PERMISSIONS_FILE" > "$TEMP_FILE"

if cmp -s "$PERMISSIONS_FILE" "$TEMP_FILE"; then
    echo "Permisos de integracion ya configurados."
    exit 0
fi

cp "$PERMISSIONS_FILE" "$PERMISSIONS_FILE.before-integration-permissions"
cat "$TEMP_FILE" > "$PERMISSIONS_FILE"
./setup.sh push
echo "Permisos de integraci�n configurados para sus cuentas. Reiniciar Bonita para aplicarlos."
