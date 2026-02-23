#!/usr/bin/env bash

set -e

echo "Building and starting containers via Docker Compose..."
make docker-up

echo "Waiting for the API to become available on http://localhost:8000..."
# Wait up to 30 seconds for the service to start
for i in {1..30}; do
  # Using curl to hit the OpenAPI /docs endpoint
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs | grep -q "200"; then
    echo "✅ API is up and responding at /docs!"
    break
  fi
  
  if [ "$i" -eq 30 ]; then
    echo "❌ Timeout waiting for API to start."
    echo "Tearing down..."
    make docker-down
    exit 1
  fi
  
  sleep 1
done

echo "Tearing down containers..."
make docker-down

echo "✅ Docker setup verified successfully!"
