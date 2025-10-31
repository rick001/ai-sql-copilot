#!/bin/bash

# CVS AI SQL Copilot - Startup Script
# This script starts all services and seeds the database

set -e

COMPOSE_FILE="infra/docker-compose.yml"

echo "🚀 Starting CVS AI SQL Copilot..."
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from env.example..."
    cp infra/env.example .env
    echo "✅ Created .env file. Please review and update it if needed."
    echo ""
fi

# Check if Docker is running, and try to start Colima if not
if ! docker info > /dev/null 2>&1; then
    echo "🐳 Docker is not running. Attempting to start..."
    echo ""
    
    if command -v colima > /dev/null 2>&1; then
        echo "Starting Colima..."
        if ! colima start; then
            echo "❌ Failed to start Colima. Please start it manually: colima start"
            exit 1
        fi
        
        echo "⏳ Waiting for Docker to be ready..."
        sleep 3
        
        max_attempts=30
        attempt=0
        while [ $attempt -lt $max_attempts ]; do
            if docker info > /dev/null 2>&1; then
                echo "✅ Docker is ready!"
                break
            fi
            attempt=$((attempt + 1))
            sleep 1
        done
        
        if ! docker info > /dev/null 2>&1; then
            echo "❌ Docker did not start in time. Please check Colima manually."
            exit 1
        fi
    else
        echo "❌ Error: Docker is not running and Colima is not installed."
        echo ""
        echo "Please start Docker:"
        echo "  - Docker Desktop: Open Docker Desktop application"
        echo "  - Colima:         Install with 'brew install colima' then run 'colima start'"
        echo ""
        exit 1
    fi
fi

# Start services
echo "Building and starting services..."
if ! docker compose -f "$COMPOSE_FILE" up -d --build; then
    echo "❌ Failed to start services. Please check the error messages above."
    exit 1
fi

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 8

# Seed the database
echo "🌱 Seeding database..."
if docker compose -f "$COMPOSE_FILE" exec -T backend python -m app.seed; then
    echo "✅ Database seeded successfully!"
else
    echo "⚠️  Warning: Seeding failed, but services are running."
    echo "   You can run 'make seed' or 'docker compose -f $COMPOSE_FILE exec backend python -m app.seed' manually."
fi

echo ""
echo "✅ System is ready!"
echo ""
echo "📍 Access points:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   Health:    http://localhost:8000/healthz"
echo ""
echo "💡 Useful commands:"
echo "   View logs:  docker compose -f $COMPOSE_FILE logs -f"
echo "   Stop:       docker compose -f $COMPOSE_FILE down"
echo "   Or use:     make logs / make stop"
echo ""

