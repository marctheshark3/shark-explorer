#!/bin/bash

set -e

# Function to check if a service is healthy
check_service() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    echo "Checking $service health..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:${2}/health" > /dev/null; then
            echo "$service is healthy!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "$service failed to become healthy after $max_attempts attempts"
    return 1
}

# Create backup directory if it doesn't exist
mkdir -p backups

# Backup existing data if containers are running and postgres container exists
if docker ps -q -f name=postgres >/dev/null 2>&1; then
    echo "Creating database backup..."
    docker exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql || {
        echo "Warning: Database backup failed, but continuing with deployment..."
    }
else
    echo "No existing PostgreSQL container found, skipping backup..."
fi

# Copy .env.prod to .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.prod..."
    cp .env.prod .env
fi

# Pull latest changes
echo "Pulling latest changes..."
git pull origin main || {
    echo "Warning: Git pull failed, continuing with local files..."
}

# Build and start services
echo "Building and starting services..."
docker compose -f docker-compose.prod.yml down || true
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
echo "Waiting 30 seconds for services to initialize..."
sleep 30

check_service "API" "8082" || {
    echo "Warning: API health check failed, but continuing..."
}

# Check monitoring services
echo "Checking monitoring services..."
curl -s "http://localhost:9090/-/healthy" > /dev/null && echo "Prometheus is healthy!" || echo "Prometheus health check failed!"
curl -s "http://localhost:3000/api/health" > /dev/null && echo "Grafana is healthy!" || echo "Grafana health check failed!"

echo "Deployment completed! You can now access:"
echo "- API: http://localhost:8082"
echo "- Grafana: http://localhost:3000"
echo "- Prometheus: http://localhost:9090" 