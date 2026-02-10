#!/bin/bash

# HestaTrack Deployment Script

echo "Starting deployment..."

# 1. Check if tools are installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is missing. Please install it."
    exit 1
fi

if ! command -v mkcert &> /dev/null; then
    echo "Error: mkcert is missing. Please install it."
    exit 1
fi

# 2. handle SSL Certs
if [ ! -f "./certs/cert.pem" ]; then
    echo "Creating SSL certificates..."
    mkdir -p ./certs
    cd ./certs
    mkcert -key-file key.pem -cert-file cert.pem localhost 127.0.0.1 hestadashboard.com
    cd ..
else
    echo "SSL certificates found."
fi

# 3. Stop old containers and start fresh
echo "Rebuilding and starting Docker containers..."
docker compose down
docker compose up -d --build

# 4. Wait for Database and Backend to be ready
echo "Waiting for services to start..."

# Wait for Mongo
until [ "$(docker inspect -f {{.State.Health.Status}} hesta_mongo)" == "healthy" ]; do
    sleep 2
done
echo "Database is ready."

# Wait for Backend
until [ "$(docker inspect -f {{.State.Health.Status}} hesta_backend)" == "healthy" ]; do
    sleep 2
done
echo "Backend is ready."

# 5. Seed the database if the file exists
if [ -f "seed.js" ]; then
    echo "Seeding database..."
    # Copy file into container and run it
    docker cp seed.js hesta_backend:/app/seed.js
    docker exec hesta_backend node seed.js
fi

echo ""
echo "Deployment successful!"
echo "Site is live at: https://hestadashboard.com"