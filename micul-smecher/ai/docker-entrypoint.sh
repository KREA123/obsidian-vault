#!/bin/sh
# Platform volumes (e.g. Fly) are mounted root-owned: fix /data, then drop to the unprivileged user.
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p "${SOUL_DATA_DIR:-/data}"
  chown -R soul:soul "${SOUL_DATA_DIR:-/data}"
  chmod 0700 "${SOUL_DATA_DIR:-/data}"
  exec setpriv --reuid=soul --regid=soul --init-groups "$@"
fi
exec "$@"
