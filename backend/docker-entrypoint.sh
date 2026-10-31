#!/bin/sh
set -eu

# Migrations are deliberately an explicit deployment command.
python manage.py collectstatic --noinput
exec "$@"