#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -c 'import sys; sys.exit(sys.version_info < (3,10))'
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python server.py
