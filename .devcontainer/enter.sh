#!/bin/bash
# Enter the pi development container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if container is running
if ! docker-compose ps | grep -q "pi-dev"; then
    echo "Starting pi development container..."
    docker-compose up -d
    echo "Installing dependencies..."
    docker-compose exec pi-dev npm ci
fi

echo "Entering pi development container..."
docker-compose exec pi-dev bash
