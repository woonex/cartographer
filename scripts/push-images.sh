#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT/infra"

echo "Reading ECR URLs from Terraform outputs..."
ECR=$(terraform output -json ecr_urls)

FRONTEND=$(echo "$ECR" | python3 -c "import sys,json; print(json.load(sys.stdin)['frontend'])")
INGESTION=$(echo "$ECR" | python3 -c "import sys,json; print(json.load(sys.stdin)['ingestion'])")
QUERY=$(echo "$ECR" | python3 -c "import sys,json; print(json.load(sys.stdin)['query'])")
VEHICLE=$(echo "$ECR" | python3 -c "import sys,json; print(json.load(sys.stdin)['vehicle-library'])")
SPEC=$(echo "$ECR" | python3 -c "import sys,json; print(json.load(sys.stdin)['specification-library'])")

REGISTRY=$(echo "$FRONTEND" | cut -d/ -f1)

echo "Authenticating Docker to ECR..."
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin "$REGISTRY"

cd "$REPO_ROOT"

echo "Tagging images..."
docker tag cartographer-frontend              "$FRONTEND:latest"
docker tag cartographer-ingestion             "$INGESTION:latest"
docker tag cartographer-query                 "$QUERY:latest"
docker tag cartographer-vehicle_library       "$VEHICLE:latest"
docker tag cartographer-specification_library "$SPEC:latest"

echo "Pushing images..."
docker push "$FRONTEND:latest"
docker push "$INGESTION:latest"
docker push "$QUERY:latest"
docker push "$VEHICLE:latest"
docker push "$SPEC:latest"

echo "Done."
