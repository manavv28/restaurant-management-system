#!/usr/bin/env bash
# Run in Google Cloud Shell from this checkout. No secrets are passed in command arguments.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PROJECT_ID:?Set PROJECT_ID to your Google Cloud project ID}"
REGION="${REGION:-asia-south1}"
SERVICE=biteai-api
REPOSITORY=biteai
RUNTIME_ACCOUNT="biteai-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
BUILD_ACCOUNT="biteai-build@${PROJECT_ID}.iam.gserviceaccount.com"
SOURCE_BUCKET="${PROJECT_ID}-biteai-build-source"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/api:$(git rev-parse --short HEAD)"
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com
if ! gcloud iam service-accounts describe "$RUNTIME_ACCOUNT" >/dev/null 2>&1; then
  gcloud iam service-accounts create biteai-runtime --display-name="BiteAI runtime"
fi
if ! gcloud iam service-accounts describe "$BUILD_ACCOUNT" >/dev/null 2>&1; then
  gcloud iam service-accounts create biteai-build --display-name="BiteAI build"
fi
for required_secret in biteai-database-url biteai-jwt-secret; do
  # Values must already exist in Secret Manager. Abort before creating a billable workload.
  gcloud secrets versions access latest --secret="$required_secret" >/dev/null
  gcloud secrets add-iam-policy-binding "$required_secret" --member="serviceAccount:$RUNTIME_ACCOUNT" --role=roles/secretmanager.secretAccessor >/dev/null
done
if ! gcloud artifacts repositories describe "$REPOSITORY" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" --repository-format=docker --location="$REGION"
fi
gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY" --location="$REGION" --member="serviceAccount:$BUILD_ACCOUNT" --role=roles/artifactregistry.writer >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$BUILD_ACCOUNT" --role=roles/logging.logWriter >/dev/null
if ! gcloud storage buckets describe "gs://$SOURCE_BUCKET" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$SOURCE_BUCKET" --location="$REGION" --uniform-bucket-level-access
fi
gcloud storage buckets add-iam-policy-binding "gs://$SOURCE_BUCKET" --member="serviceAccount:$BUILD_ACCOUNT" --role=roles/storage.objectViewer >/dev/null
gcloud builds submit --config=deploy/cloudbuild.yaml --service-account="projects/$PROJECT_ID/serviceAccounts/$BUILD_ACCOUNT" --gcs-source-staging-dir="gs://$SOURCE_BUCKET/source" --substitutions="_IMAGE=$IMAGE" .

COMMON_ENV="APP_ENV=production,AUTO_CREATE_SCHEMA=false,SEED_SAMPLE_DATA=false,ENABLE_PAYMENT_SIMULATION=false"
COMMON_SECRETS="DATABASE_URL=biteai-database-url:latest,JWT_SECRET=biteai-jwt-secret:latest"
# The migration must succeed before the API revision is deployed.
gcloud run jobs deploy biteai-migrate --image="$IMAGE" --region="$REGION" --service-account="$RUNTIME_ACCOUNT" --args=migrate --update-env-vars="$COMMON_ENV" --update-secrets="$COMMON_SECRETS" --tasks=1 --max-retries=0 --task-timeout=300s --memory=512Mi
gcloud run jobs execute biteai-migrate --region="$REGION" --wait

gcloud run deploy "$SERVICE" --image="$IMAGE" --region="$REGION" --service-account="$RUNTIME_ACCOUNT" --allow-unauthenticated --port=8080 --min-instances=0 --max-instances=2 --concurrency=4 --cpu=1 --memory=512Mi --update-env-vars="$COMMON_ENV" --update-secrets="$COMMON_SECRETS"
gcloud run jobs deploy biteai-collect --image="$IMAGE" --region="$REGION" --service-account="$RUNTIME_ACCOUNT" --args=collect,--limit,5 --update-env-vars="$COMMON_ENV" --update-secrets="$COMMON_SECRETS" --tasks=1 --max-retries=0 --task-timeout=600s --memory=512Mi
gcloud run jobs deploy biteai-retain --image="$IMAGE" --region="$REGION" --service-account="$RUNTIME_ACCOUNT" --args=retain --update-env-vars="$COMMON_ENV" --update-secrets="$COMMON_SECRETS" --tasks=1 --max-retries=0 --task-timeout=300s --memory=512Mi
API_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
curl --fail --silent --show-error --max-time 60 "$API_URL/health"
printf '\nSet Vercel API_INTERNAL_URL to: %s\nThen redeploy the frontend. Do not append /api.\n' "$API_URL"
