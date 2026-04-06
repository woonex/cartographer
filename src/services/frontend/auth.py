"""
Gradio auth verifier backed by AWS Secrets Manager.

The secret is a JSON object mapping usernames to bcrypt-hashed passwords:
  {"alice": "$2b$12$...", "bob": "$2b$12$..."}

To add or revoke a user, update the secret — no redeploy required.

Falls back to no authentication if the secret name is not configured (local dev).
"""

import json

import bcrypt
import boto3


def _fetch_users(secret_name: str) -> dict[str, str]:
    client = boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=secret_name)
    return json.loads(resp["SecretString"])


def build_auth_verifier(secret_name: str):
    """Returns a Gradio-compatible auth callable, or None if secret_name is empty."""
    if not secret_name:
        return None

    try:
        users = _fetch_users(secret_name)
    except Exception:
        print("Auth secret unavailable — running without authentication", flush=True)
        return None

    def verify(username: str, password: str) -> bool:
        stored = users.get(username)
        if not stored:
            return False
        return bcrypt.checkpw(password.encode(), stored.encode())

    return verify
