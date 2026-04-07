#!/usr/bin/env bash
set -euo pipefail

CLUSTER="cartographer"
SERVICES=(
  cartographer-frontend
  cartographer-query
  cartographer-ingestion
  cartographer-vehicle-library
  cartographer-specification-library
)

for SERVICE in "${SERVICES[@]}"; do
  echo "Redeploying $SERVICE..."
  aws ecs update-service \
    --cluster "$CLUSTER" \
    --service "$SERVICE" \
    --force-new-deployment \
    --no-cli-pager \
    --query "service.serviceName" \
    --output text
done

echo "Done. Tasks are restarting — check ECS console for status."
