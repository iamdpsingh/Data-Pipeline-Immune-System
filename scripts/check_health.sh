#!/usr/bin/env bash
set -euo pipefail
API_URL="${CLOUD_RUN_URL:-http://localhost:8080}"
echo "Pinging Autonomous Controller at ${API_URL}/health..."
curl -fsS "${API_URL}/health" || echo "Controller offline or local"
