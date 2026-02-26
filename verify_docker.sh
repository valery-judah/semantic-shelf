#!/usr/bin/env bash

set -euo pipefail

cleaned_up=0
cleanup() {
  if [ "${cleaned_up}" -eq 0 ]; then
    echo "Tearing down containers..."
    make down
    cleaned_up=1
  fi
}

trap cleanup EXIT INT TERM

echo "Building and starting containers via Docker Compose..."
make up-build

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
    exit 1
  fi
  
  sleep 1
done

echo "✅ Docker setup verified successfully!"
