#!/bin/sh
set -eu
PORTAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PORTAL_DIR"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.10 or newer is required. Install Python, then run this launcher again.' >&2
  exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else "Python 3.10 or newer is required.")'
exec python3 "$PORTAL_DIR/server.py" --open-browser
