#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <username>"
  exit 1
fi

USERNAME=$1
read -rsp "Password for $USERNAME: " PASSWORD
echo
SECRET_ID="cartographer/frontend-auth-users"

echo "Hashing password..."
HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'${PASSWORD}', bcrypt.gensalt()).decode())")

echo "Fetching existing users..."
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" \
  --query SecretString \
  --output text \
  --no-cli-pager 2>/dev/null || echo '{}')

echo "Updating secret..."
NEW=$(echo "$CURRENT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
d['${USERNAME}'] = '${HASH}'
print(json.dumps(d))
")

aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ID" \
  --secret-string "$NEW" \
  --no-cli-pager

echo "Added user: $USERNAME"
