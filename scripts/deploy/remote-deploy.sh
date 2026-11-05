#!/usr/bin/env bash
# Se ejecuta en el droplet: el workflow envía exports + este script por stdin y el
# shell remoto lo evalúa tras leer TODO el stdin (así ningún docker puede consumirlo).
# Recibe la configuración como variables de entorno; nunca escribe secretos a disco.
# DEPLOY_CHECK_ONLY=1 valida variables y compone DATABASE_URL sin tocar Docker.
set -euo pipefail

required=(IMAGE_TAG DEPLOY_PATH DATABASE_NETWORK SECRET_KEY DB_USER DB_PASSWORD DB_NAME)
missing=()
for name in "${required[@]}"; do
  [ -n "${!name:-}" ] || missing+=("$name")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "Faltan variables requeridas: ${missing[*]}" >&2
  exit 1
fi
case "$DEPLOY_PATH" in
  /*) ;;
  *) echo "DEPLOY_PATH debe ser una ruta absoluta" >&2; exit 1 ;;
esac

DB_HOST="${DB_HOST:-db_v2}"
DB_PORT="${DB_PORT:-5432}"
DB_CONTAINER="${DB_CONTAINER:-db_v2}"
KEEP_RELEASES="${KEEP_RELEASES:-5}"
KEEP_BACKUPS="${KEEP_BACKUPS:-10}"

urlencode() {
  local LC_ALL=C s="$1" out="" c h i
  for ((i = 0; i < ${#s}; i++)); do
    c="${s:i:1}"
    case "$c" in
      [a-zA-Z0-9.~_-]) out+="$c" ;;
      *) printf -v h '%%%02X' "'$c"; out+="$h" ;;
    esac
  done
  printf '%s' "$out"
}

DATABASE_URL="postgresql://$(urlencode "$DB_USER"):$(urlencode "$DB_PASSWORD")@${DB_HOST}:${DB_PORT}/$(urlencode "$DB_NAME")"

if [ "${DEPLOY_CHECK_ONLY:-0}" = "1" ]; then
  echo "DATABASE_URL=${DATABASE_URL}"
  exit 0
fi

export DATABASE_URL SECRET_KEY IMAGE_TAG DATABASE_NETWORK
[ -z "${TIME_ZONE:-}" ] || export TIME_ZONE
[ -z "${REGISTRATION_ENABLED:-}" ] || export REGISTRATION_ENABLED

umask 077
cd "$DEPLOY_PATH"
mkdir -p backups

echo "==> Validando compose"
docker compose config --quiet </dev/null

echo "==> Backup de la base de datos (INV-01)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="backups/${DB_NAME}-${stamp}-${IMAGE_TAG}.sql.gz"
export PGPASSWORD="$DB_PASSWORD"
if ! docker exec -e PGPASSWORD "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "${backup}.tmp"; then
  rm -f "${backup}.tmp"
  echo "El backup falló; se aborta sin migrar" >&2
  exit 1
fi
unset PGPASSWORD
mv "${backup}.tmp" "$backup"
# shellcheck disable=SC2012
ls -1t backups/*.sql.gz 2>/dev/null | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm --

echo "==> Migraciones (INV-02: si fallan, no se reemplazan los contenedores)"
docker compose run --rm -T --no-deps backend python manage.py migrate --noinput </dev/null

echo "==> Levantando la versión ${IMAGE_TAG}"
docker compose up -d --no-build --wait </dev/null
docker compose ps </dev/null

echo "==> Limpiando imágenes antiguas (se conservan ${KEEP_RELEASES})"
for repo in pocketbiz-backend pocketbiz-frontend; do
  docker image ls "$repo" --format '{{.Tag}}' \
    | { grep -v -x -e "$IMAGE_TAG" -e latest -e '<none>' || true; } \
    | tail -n +"$KEEP_RELEASES" \
    | while read -r tag; do docker rmi "${repo}:${tag}" </dev/null >/dev/null 2>&1 || true; done
done
echo "==> Deploy ${IMAGE_TAG} completado"
