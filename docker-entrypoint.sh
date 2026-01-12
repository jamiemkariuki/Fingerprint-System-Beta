#!/bin/sh
set -e

# Start pigpio daemon if available (for GPIO access inside container)
if command -v pigpiod >/dev/null 2>&1; then
  echo "Starting pigpiod..."
  pigpiod -s 1 >/dev/null 2>&1 || true
  sleep 0.5
fi

exec "$@"
