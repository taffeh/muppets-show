#!/bin/bash
# Apply a Model Armor template version to the live template.
#
# Usage:
#   ./apply.sh template_v2.json
#
# Prerequisites:
#   gcloud auth login  (or Application Default Credentials)
#   GOOGLE_CLOUD_PROJECT env var set, or pass as second arg
#
# The script PATCHes only filterConfig, leaving display name / labels intact.

set -euo pipefail

TEMPLATE_FILE="${1:-template_v2.json}"
PROJECT="${2:-${GOOGLE_CLOUD_PROJECT:-teletraan-one}}"
LOCATION="europe-west2"
TEMPLATE_ID="my-first-template"

BASE_URL="https://modelarmor.${LOCATION}.rep.googleapis.com/v1"
TEMPLATE_NAME="projects/${PROJECT}/locations/${LOCATION}/templates/${TEMPLATE_ID}"

echo "Fetching access token..."
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Applying ${TEMPLATE_FILE} to ${TEMPLATE_NAME}..."
curl -s -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  "${BASE_URL}/${TEMPLATE_NAME}?updateMask=filterConfig" \
  -d "@${TEMPLATE_FILE}" \
  | python3 -m json.tool

echo ""
echo "Done. Verifying live template..."
curl -s \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${BASE_URL}/${TEMPLATE_NAME}" \
  | python3 -m json.tool
