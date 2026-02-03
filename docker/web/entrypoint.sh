#!/usr/bin/env bash
set -e

echo "DB_HOST=$DB_HOST"
echo "MEDIA_ROOT=$MEDIA_ROOT"
echo "TEMP_ROOT=$TEMP_ROOT"
echo "MEDIA_URL=$MEDIA_URL"

mkdir -p "$MEDIA_ROOT/images" "$MEDIA_ROOT/thumbs" "$MEDIA_ROOT/crops"
mkdir -p "$TEMP_ROOT/img" "$TEMP_ROOT/json" "$TEMP_ROOT/thumbs"

exec gunicorn \
  --workers 4 \
  --threads 1 \
  --timeout 600 \
  --bind 0.0.0.0:5000 \
  "app:create_app()"
