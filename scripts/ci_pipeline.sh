#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
# Treat unset variables as an error.
set -euo pipefail

echo "========================================"
echo "🚀 Starting CI Pipeline..."
echo "========================================"

echo ""
echo "📦 1. Installing dependencies..."
make install

echo ""
echo "🧹 2. Running Linters & Formatters..."
# Using the pre-configured make targets
make lint

echo ""
echo "🔎 3. Running Type Checks..."
make type

echo ""
echo "🧪 4. Running Tests..."
make test

echo ""
echo "📄 5. Building OpenAPI / Swagger Spec..."
# Generate the docs/openapi.json static file
make openapi

# Optional: In a true CI environment, check for uncommitted spec changes to avoid drift
# if ! git diff --exit-code docs/openapi.json > /dev/null; then
#   echo "❌ Error: OpenAPI spec is out of date! Run 'make openapi' and commit the changes."
#   exit 1
# fi
echo "✅ OpenAPI spec generated successfully at docs/openapi.json (ready as a build artifact)"

echo ""
echo "🐳 6. Building Docker Image..."
make build

echo ""
echo "📊 7. Running Evaluation Smoke Test..."
# Run the smoke scenario and gate on correctness/performance
# We skip the build here since we just built it in step 6
uv run python scripts/ci_eval.py --scenario similar_books_smoke --no-build

echo ""
echo "========================================"
echo "🎉 CI Pipeline completed successfully!"
echo "========================================"
