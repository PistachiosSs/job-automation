#!/usr/bin/env bash
# Job Apply launcher for macOS / Linux:  ./start.sh [--port 8766] [--no-browser]
set -e
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
if [ -d /Library/TeX/texbin ]; then export PATH="/Library/TeX/texbin:$PATH"; fi
if [ ! -f config.json ]; then
  echo "No config.json found - running first-time setup."
  "$PY" setup.py
fi
echo "Starting Job Apply (keep this window open; press Ctrl+C to stop)"
exec "$PY" app/server.py "$@"
