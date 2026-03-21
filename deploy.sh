#!/bin/bash
# deploy.sh — Docker based deployment
# Assumes code is already cloned at /root/Odoo-Middleware
# Usage: bash deploy.sh

set -e

APP_DIR="/root/Odoo-Middleware"
IMAGE_NAME="odoo-middleware"
CONTAINER_NAME="odoo-middleware"

echo "==> Moving to app directory"
cd $APP_DIR

echo "==> Stopping existing container if running"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "==> Building Docker image"
docker build -t $IMAGE_NAME .

echo "==> Starting container"
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  --network host \
  --env-file .env \
  $IMAGE_NAME

echo ""
echo "✅ Done! Container is running."
echo ""
echo "Useful commands:"
echo "  docker ps                          # check if running"
echo "  docker logs $CONTAINER_NAME -f    # live logs"
echo "  docker restart $CONTAINER_NAME    # restart"
echo "  docker stop $CONTAINER_NAME       # stop"