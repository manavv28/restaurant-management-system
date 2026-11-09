#!/usr/bin/env bash
# Optional: creates hourly collection and daily retention schedules (billing may apply).
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID first}"
REGION="${REGION:-asia-south1}"
SCHEDULER_ACCOUNT="biteai-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud config set project "$PROJECT_ID"
if ! gcloud iam service-accounts describe "$SCHEDULER_ACCOUNT" >/dev/null 2>&1; then
  gcloud iam service-accounts create biteai-scheduler --display-name="BiteAI scheduled jobs"
fi
for job in biteai-collect biteai-retain; do
  gcloud run jobs add-iam-policy-binding "$job" --region="$REGION" --member="serviceAccount:$SCHEDULER_ACCOUNT" --role=roles/run.invoker >/dev/null
  schedule='0 * * * *'
  if [ "$job" = biteai-retain ]; then schedule='30 3 * * *'; fi
  operation=create
  if gcloud scheduler jobs describe "$job" --location="$REGION" >/dev/null 2>&1; then operation=update; fi
  gcloud scheduler jobs "$operation" http "$job" --location="$REGION" --schedule="$schedule" --time-zone=Asia/Kolkata --uri="https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/$job:run" --http-method=POST --oauth-service-account-email="$SCHEDULER_ACCOUNT" --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform --headers=Content-Type=application/json --message-body='{}' --attempt-deadline=60s
done
