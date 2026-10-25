#!/bin/sh
set -eu
PORTAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec /bin/sh "$PORTAL_DIR/start.sh"
