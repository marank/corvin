#!/bin/sh
# Runs the given command once a day at RUN_AT (HH:MM, container time zone TZ).
# Used by the "scheduler" service in docker-compose.yml.
set -u

time="${RUN_AT:-06:00}"
echo "daily: '$*' at $time"
last=""
while :; do
  now="$(date +%H:%M)"
  today="$(date +%F)"
  if [ "$now" = "$time" ] && [ "$last" != "$today" ]; then
    if "$@"; then last="$today"; else echo "daily: FAILED: $*" >&2; fi
  fi
  sleep 30
done
