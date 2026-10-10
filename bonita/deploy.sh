#!/bin/sh

set -eu
set -x

ARTIFACTS_DIR="/opt/bonita/artifacts"

BONITA_URL="http://localhost:8080/bonita"
COOKIE_FILE="/tmp/bonita-cookies.txt"

ORGANIZATION_FILE="$ARTIFACTS_DIR/RESCUE.xml"

BAR_FILE=$(find "$ARTIFACTS_DIR" -type f -name "*.bar" | head -1)

USER_PROFILE_ID="1"
ADMIN_PROFILE_ID="2"

bonita_login() {
  curl -v \
    -c "$COOKIE_FILE" \
    -X POST \
    "$BONITA_URL/loginservice" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -H "Accept: application/json" \
    --data-urlencode "username=tech_user" \
    --data-urlencode "password=secret" \
    --data-urlencode "redirect=false" \
    "$@"
}

bonita_curl() {
  curl \
    -b "$COOKIE_FILE" \
    -H "X-Bonita-API-Token: $X_BONITA_TOKEN" \
    "$@"
}

bonita_curl_verbose() {
  bonita_curl -v "$@"
}

bonita_curl_fail() {
  bonita_curl --fail --silent --show-error "$@"
}

bonita_curl_json() {
  bonita_curl \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    "$@"
}

bonita_curl_json_fail() {
  bonita_curl_fail \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    "$@"
}

bonita_curl_query() {
  bonita_curl -G "$@"
}

echo "==================================="
echo "Bonita Deploy Script"
echo "==================================="

# --------------------------------------------------
# Validaciones iniciales
# --------------------------------------------------

if [ ! -f "$ORGANIZATION_FILE" ]; then
  echo "ERROR: no existe el archivo de organización:"
  echo "$ORGANIZATION_FILE"
  exit 1
fi

if [ -z "$BAR_FILE" ] || [ ! -f "$BAR_FILE" ]; then
  echo "ERROR: no se encontró ningún archivo .bar"
  exit 1
fi

if [ -z "${BONITA_PROCESS:-}" ]; then
  echo "ERROR: BONITA_PROCESS no está definida"
  exit 1
fi

echo "Organización: $ORGANIZATION_FILE"
echo "BAR:          $BAR_FILE"
echo "Proceso Bonita: $BONITA_PROCESS"

# --------------------------------------------------
# Esperar a Bonita
# --------------------------------------------------

echo ""
echo "Esperando a Bonita..."

until curl -sf "$BONITA_URL" > /dev/null; do
  sleep 2
done

echo "Bonita disponible"

# --------------------------------------------------
# Login
# --------------------------------------------------

echo ""
echo "Iniciando sesión..."

rm -f "$COOKIE_FILE"

bonita_login \
  > /dev/null

X_BONITA_TOKEN=$(
  awk '$6=="X-Bonita-API-Token" {print $7}' "$COOKIE_FILE"
)

if [ -z "$X_BONITA_TOKEN" ]; then
  echo "ERROR: no fue posible obtener X-Bonita-API-Token"
  exit 1
fi

echo "Login correcto"

# --------------------------------------------------
# Importar organización
# --------------------------------------------------

echo ""
echo "Importando organización..."

if [ ! -f "$ORGANIZATION_FILE" ]; then
  echo "ERROR: No existe el archivo de organización: $ORGANIZATION_FILE"
  exit 1
fi

ORGANIZATION_UPLOAD_URL="$BONITA_URL/portal/resource/app/superAdminAppBonita/install-export-organization/API/formFileUpload"
ORGANIZATION_IMPORT_URL="$BONITA_URL/portal/resource/app/superAdminAppBonita/install-export-organization/API/services/organization/import"

echo "1/2 Subiendo XML de organización..."

UPLOAD_RESPONSE=$(
  bonita_curl_fail \
    -F "pbUpload0=@${ORGANIZATION_FILE};type=text/xml" \
    -F "CSRFToken=${X_BONITA_TOKEN}" \
    "$ORGANIZATION_UPLOAD_URL"
)

echo "Respuesta de carga:"
echo "$UPLOAD_RESPONSE"

TEMP_PATH=$(
  echo "$UPLOAD_RESPONSE" |
    sed -n 's/.*"tempPath"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'
)

if [ -z "$TEMP_PATH" ]; then
  echo "ERROR: Bonita no devolvió el tempPath del XML."
  echo "Respuesta recibida:"
  echo "$UPLOAD_RESPONSE"
  exit 1
fi

echo "Archivo temporal generado: $TEMP_PATH"
echo "2/2 Instalando organización..."

IMPORT_PAYLOAD=$(printf '{"organizationDataUpload":"%s"}' "$TEMP_PATH")

bonita_curl_json_fail \
  -X POST \
  --data "$IMPORT_PAYLOAD" \
  "$ORGANIZATION_IMPORT_URL"

echo
echo "Organización importada correctamente"


# --------------------------------------------------
# Subir BAR
# --------------------------------------------------

echo "Buscar proceso: $BONITA_PROCESS"

EXISTING_PROCESS_ID=$(
  bonita_curl_query \
    -s \
    --data-urlencode "p=0" \
    --data-urlencode "c=20" \
    --data-urlencode "f=name=$BONITA_PROCESS" \
    "$BONITA_URL/API/bpm/process" |
  sed -n 's/.*"id":"\([^"]*\)".*/\1/p' |
  head -1
)
echo "Proceso existente ID: $EXISTING_PROCESS_ID"

if [ -n "$EXISTING_PROCESS_ID" ]; then
    echo "Proceso existente encontrado: $EXISTING_PROCESS_ID"

    echo "Desactivando..."
    bonita_curl_json_fail \
      -v \
      -X PUT \
      -d '{"activationState":"DISABLED"}' \
      "$BONITA_URL/API/bpm/process/$EXISTING_PROCESS_ID"

    echo "Eliminando..."
    bonita_curl_fail \
      -X DELETE \
      "$BONITA_URL/API/bpm/process/$EXISTING_PROCESS_ID"
fi

echo ""
echo "Subiendo BAR..."

PROCESS_UPLOAD=$(
  bonita_curl_verbose \
    -F "file=@${BAR_FILE}" \
    "$BONITA_URL/portal/processUpload"
)

if [ -z "$PROCESS_UPLOAD" ]; then
  echo "ERROR: Bonita no devolvió el identificador del BAR"
  exit 1
fi

echo "BAR subido: $PROCESS_UPLOAD"

# --------------------------------------------------
# Instalar proceso
# --------------------------------------------------

echo ""
echo "Instalando proceso..."

PROCESS=$(
  bonita_curl_json_fail \
    -v \
    -X POST \
    -d "{\"fileupload\":\"$PROCESS_UPLOAD\"}" \
    "$BONITA_URL/API/bpm/process"
)

PROCESS_ID=$(
  printf '%s' "$PROCESS" |
    sed -n 's/.*"id":"\([^"]*\)".*/\1/p'
)

# --------------------------------------------------
# Activar proceso
# --------------------------------------------------

if [ -z "$PROCESS_ID" ]; then
  echo "ERROR: No se pudo obtener el ID del proceso"
  exit 1
fi
echo "Activando proceso..."

bonita_curl_json_fail \
  -s \
  -X PUT \
  -d '{"activationState":"ENABLED"}' \
  "$BONITA_URL/API/bpm/process/$PROCESS_ID"

echo "Proceso activado"

CONFIGURATION_STATE=$(
  printf '%s' "$PROCESS" |
    sed -n 's/.*"configurationState":"\([^"]*\)".*/\1/p'
)

echo "Estado de configuración del proceso: $CONFIGURATION_STATE"

# --------------------------------------------------
# Helpers para grupos y roles
# --------------------------------------------------

delete_profile_memberships() {
    PROFILE_ID="$1"

    RESPONSE=$(
        bonita_curl_query \
            -s \
            --data-urlencode "p=0" \
            --data-urlencode "c=200" \
            --data-urlencode "f=profile_id=$PROFILE_ID" \
            --data-urlencode "f=member_type=roleAndGroup" \
            "$BONITA_URL/API/portal/profileMember"
    )

    IDS=$(
        echo "$RESPONSE" |
        grep -o '"id":"[^"]*"' |
        sed 's/"id":"//;s/"//'
    )

    for ID in $IDS; do
        echo "Eliminando profileMember $ID"

        bonita_curl_fail \
            -X DELETE \
            "$BONITA_URL/API/portal/profileMember/$ID"
    done
}

get_group_id() {
  GROUP_NAME="$1"
  GROUP_PARENT_PATH="$2"

  RESPONSE=$(
    bonita_curl_query \
      -v \
      --data-urlencode "p=0" \
      --data-urlencode "c=10" \
      --data-urlencode "f=name=$GROUP_NAME" \
      --data-urlencode "f=parent_path=$GROUP_PARENT_PATH" \
      "$BONITA_URL/API/identity/group"
  )

  GROUP_ID=$(
    printf '%s' "$RESPONSE" |
      sed -n 's/.*"id":"\([^"]*\)".*/\1/p' |
      head -1
  )

  if [ -z "$GROUP_ID" ]; then
    echo "ERROR: no se encontró el grupo $GROUP_PARENT_PATH/$GROUP_NAME" >&2
    echo "Respuesta: $RESPONSE" >&2
    exit 1
  fi

  printf '%s' "$GROUP_ID"
}

get_role_id() {
  ROLE_NAME="$1"

  RESPONSE=$(
    bonita_curl_query \
      -v \
      --data-urlencode "p=0" \
      --data-urlencode "c=10" \
      --data-urlencode "f=name=$ROLE_NAME" \
      "$BONITA_URL/API/identity/role"
  )

  ROLE_ID=$(
    printf '%s' "$RESPONSE" |
      sed -n 's/.*"id":"\([^"]*\)".*/\1/p' |
      head -1
  )

  if [ -z "$ROLE_ID" ]; then
    echo "ERROR: no se encontró el rol $ROLE_NAME" >&2
    echo "Respuesta: $RESPONSE" >&2
    exit 1
  fi

  printf '%s' "$ROLE_ID"
}

# --------------------------------------------------
# Recuperar IDs
# --------------------------------------------------

echo ""
echo "Recuperando IDs de grupos..."

GROUP_MUNICIPIOS_ID=$(get_group_id "municipios" "/rescue")
GROUP_ONGS_ID=$(get_group_id "ongs" "/rescue")
GROUP_DIRECTIVOS_ID=$(get_group_id "directivos" "/rescue")
GROUP_AUDITORES_ID=$(get_group_id "auditores" "/rescue")
GROUP_COORDINADORES_ID=$(get_group_id "coordinadores" "/rescue")

echo "municipios:     $GROUP_MUNICIPIOS_ID"
echo "ongs:           $GROUP_ONGS_ID"
echo "directivos:     $GROUP_DIRECTIVOS_ID"
echo "auditores:      $GROUP_AUDITORES_ID"
echo "coordinadores:  $GROUP_COORDINADORES_ID"

echo ""
echo "Recuperando IDs de roles..."

ROLE_OPERADOR_ID=$(get_role_id "operador_municipal")
ROLE_COORDINADOR_ID=$(get_role_id "centro_coordinador")
ROLE_ONG_ID=$(get_role_id "representante_ong")
ROLE_AUDITOR_ID=$(get_role_id "auditor")
ROLE_DIRECTIVO_ID=$(get_role_id "directivo")

echo "operador_municipal:  $ROLE_OPERADOR_ID"
echo "centro_coordinador:  $ROLE_COORDINADOR_ID"
echo "representante_ong:   $ROLE_ONG_ID"
echo "auditor:             $ROLE_AUDITOR_ID"
echo "directivo:           $ROLE_DIRECTIVO_ID"

# --------------------------------------------------
# Profile members
# --------------------------------------------------

add_profile_membership() {
  PROFILE_ID="$1"
  GROUP_ID="$2"
  ROLE_ID="$3"
  DESCRIPTION="$4"

  echo "Creando: $DESCRIPTION"

  RESPONSE=$(
    bonita_curl_json_fail \
      -v \
      -X POST \
      -d "{
        \"profile_id\":\"$PROFILE_ID\",
        \"group_id\":\"$GROUP_ID\",
        \"role_id\":\"$ROLE_ID\"
      }" \
      "$BONITA_URL/API/portal/profileMember"
  )

  PROFILE_MEMBER_ID=$(
    printf '%s' "$RESPONSE" |
      sed -n 's/.*"id":"\([^"]*\)".*/\1/p'
  )

  if [ -z "$PROFILE_MEMBER_ID" ]; then
    echo "ERROR: no se pudo crear $DESCRIPTION"
    echo "Respuesta: $RESPONSE"
    exit 1
  fi

  echo "Creado: $DESCRIPTION, ID $PROFILE_MEMBER_ID"
}

configure_profile() {
  PROFILE_ID="$1"
  PROFILE_NAME="$2"

  echo "Eliminando membresías del perfil $PROFILE_NAME..."
  delete_profile_memberships "$PROFILE_ID"
  echo "Membresías eliminadas del perfil $PROFILE_NAME."

  echo ""
  echo "Configurando perfil $PROFILE_NAME..."

  add_profile_membership \
    "$PROFILE_ID" \
    "$GROUP_MUNICIPIOS_ID" \
    "$ROLE_OPERADOR_ID" \
    "$PROFILE_NAME -> Municipios + Operador Municipal"

  add_profile_membership \
    "$PROFILE_ID" \
    "$GROUP_ONGS_ID" \
    "$ROLE_ONG_ID" \
    "$PROFILE_NAME -> Ongs + Representante ONG"

  add_profile_membership \
    "$PROFILE_ID" \
    "$GROUP_COORDINADORES_ID" \
    "$ROLE_COORDINADOR_ID" \
    "$PROFILE_NAME -> Coordinadores + Centro Coordinador"

  add_profile_membership \
    "$PROFILE_ID" \
    "$GROUP_DIRECTIVOS_ID" \
    "$ROLE_DIRECTIVO_ID" \
    "$PROFILE_NAME -> Directivos + Directivo"

  add_profile_membership \
    "$PROFILE_ID" \
    "$GROUP_AUDITORES_ID" \
    "$ROLE_AUDITOR_ID" \
    "$PROFILE_NAME -> Auditores + Auditor"
}

configure_profile "$USER_PROFILE_ID" "User"
configure_profile "$ADMIN_PROFILE_ID" "Administrator"

echo ""
echo "==================================="
echo "DEPLOY FINALIZADO"
echo "==================================="
echo "Proceso: $BONITA_PROCESS"
echo "ProcessId: $PROCESS_ID"
echo "User profile configurado"
echo "Administrator profile configurado"