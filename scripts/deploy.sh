#!/usr/bin/env bash
# ==============================================================================
# Data Pipeline Immune System — Cloud Run Deployment Script
# ==============================================================================
set -euo pipefail

ENV="${ENVIRONMENT:-dev}"
PROJECT_ID="${PROJECT_ID:-dpis-dev}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="dpis-${ENV}-api"
IMAGE_TAG="gcr.io/${PROJECT_ID}/immune-system:${IMAGE_VERSION:-latest}"

echo "============================================================"
echo " Deploying Data Pipeline Immune System to Cloud Run"
echo " Environment: ${ENV} | Service: ${SERVICE_NAME} | Region: ${REGION}"
echo "============================================================"

# Pre-deployment validation checks
echo "1. Running unit test suite..."
pytest tests/unit/ tests/agents/ tests/data_quality/ tests/remediation/ tests/end_to_end/ -q

echo "2. Building container image: ${IMAGE_TAG}..."
if command -v docker &>/dev/null; then
    docker build -t "${IMAGE_TAG}" .
    echo "Image built successfully."
    
    if [ "${PUSH_IMAGE:-false}" = "true" ]; then
        echo "Pushing image to registry..."
        docker push "${IMAGE_TAG}"
        
        echo "Deploying to Cloud Run..."
        gcloud run deploy "${SERVICE_NAME}" \
            --image "${IMAGE_TAG}" \
            --region "${REGION}" \
            --project "${PROJECT_ID}" \
            --set-env-vars "ENVIRONMENT=${ENV},PROJECT_ID=${PROJECT_ID}" \
            --no-allow-unauthenticated
    fi
else
    echo "Docker not detected; skipping image compilation in local testing mode."
fi

echo "Deployment workflow completed successfully."
