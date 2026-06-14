#!/bin/bash
set -e
# Fix playwright-data permissions if the volume was mounted as root
if [ -d /app/playwright-data ] && [ ! -w /app/playwright-data ]; then
    chown appuser:appuser /app/playwright-data
fi
exec gosu appuser "$@"
