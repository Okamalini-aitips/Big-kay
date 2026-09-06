#!/bin/bash
# Deployment start script for OkaMoney Web App
# This script is used for production deployment

set -e

echo "Starting OkaMoney Web App deployment..."

# Navigate to app directory
cd /app

# Build frontend if dist doesn't exist or is outdated
if [ ! -d "/app/web-frontend/dist" ]; then
    echo "Building frontend..."
    cd /app/web-frontend
    yarn install --frozen-lockfile
    yarn build
    cd /app
fi

# Start backend
echo "Starting backend on port 8001..."
cd /app/backend
/root/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 3

# Start nginx to serve frontend and proxy API
echo "Starting nginx on port 3000..."
nginx -c /app/nginx.conf -g "daemon off;" &
NGINX_PID=$!

echo "OkaMoney Web App started successfully!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8001/api"

# Wait for either process to exit
wait $BACKEND_PID $NGINX_PID
