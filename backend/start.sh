#!/usr/bin/env bash
set -e

echo ">>> START.SH EXECUTED <<<"

# Ensure file permission is correct even on Windows commits
chmod +x start.sh

uvicorn app.main:app --host 0.0.0.0 --port $PORT
