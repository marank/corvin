#!/bin/sh
# Nightly backup, run by the "backup" service in docker-compose.yml:
#   <db>-<timestamp>.dump      pg_dump, custom format (restore with pg_restore)
#   media-<timestamp>.tar.gz   uploaded files (attachments, company images, archived PDFs)
# Both go to /var/lib/postgresql/backups in the "backups" volume; files older than
# BACKUP_KEEP_DAYS are deleted.
set -eu
umask 077  # dumps contain all customer data

dir=/var/lib/postgresql/backups
time="${BACKUP_TIME:-02:30}"
keep="${BACKUP_KEEP_DAYS:-14}"
mkdir -p "$dir"

backup() {
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  file="$dir/${PGDATABASE}-$stamp.dump"
  echo "backup: writing $file"
  # Temp names first, so a failed run never looks like a valid backup.
  pg_dump --format=custom --file="$file.partial"
  mv "$file.partial" "$file"
  if [ -d /media ]; then
    echo "backup: writing $dir/media-$stamp.tar.gz"
    tar -czf "$dir/media-$stamp.tar.gz.partial" -C /media .
    mv "$dir/media-$stamp.tar.gz.partial" "$dir/media-$stamp.tar.gz"
  fi
  find "$dir" \( -name "*.dump" -o -name "*.tar.gz" \) -mtime +"$keep" -print -delete
  find "$dir" -name "*.partial" -mmin +60 -delete
}

if [ "${1:-}" = "now" ]; then
  backup
  exit 0
fi

echo "backup: daily at $time (container time zone), keeping $keep days"
last=""
while :; do
  now="$(date +%H:%M)"
  today="$(date +%F)"
  if [ "$now" = "$time" ] && [ "$last" != "$today" ]; then
    if backup; then last="$today"; else echo "backup: FAILED" >&2; fi
  fi
  sleep 30
done
