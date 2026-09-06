#!/bin/bash
# ---------------------------------------------------------------------------
# Web-app launcher shim.
# The preview environment's supervisor is hardwired to run
# `yarn expo start --port 3000` inside /app/frontend. This project is NOT an
# Expo mobile app — it is a Vite + React WEB app living in /app/web-frontend.
# This script ignores any Expo/Metro arguments and simply serves the Vite dev
# server on port 3000 so the web preview works correctly.
# ---------------------------------------------------------------------------
set -e
cd /app/web-frontend

# Ensure dependencies exist (first boot / fresh pod)
if [ ! -d node_modules ] || [ ! -x node_modules/.bin/vite ]; then
  echo "[serve-web] Installing web-frontend dependencies..."
  yarn install
fi

echo "[serve-web] Starting Vite web server on 0.0.0.0:3000"
exec yarn dev
