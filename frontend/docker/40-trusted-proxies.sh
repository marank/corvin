#!/bin/sh
# Renders TRUSTED_PROXIES (comma/space separated addresses or CIDRs) into the
# includes used by nginx.conf. Run by the nginx image's entrypoint before nginx starts.
set -eu

dir=/etc/nginx/trusted
mkdir -p "$dir"
: > "$dir/realip.conf"
: > "$dir/geo.conf"
for proxy in $(echo "${TRUSTED_PROXIES:-}" | tr ',' ' '); do
  echo "set_real_ip_from $proxy;" >> "$dir/realip.conf"
  echo "$proxy 1;" >> "$dir/geo.conf"
done
echo "trusted proxies: ${TRUSTED_PROXIES:-none}"
