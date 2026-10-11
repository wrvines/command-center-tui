#!/bin/bash
set -e
exec python3 "$(cd "$(dirname "$0")" && pwd)/manage.py" uninstall "$@"
