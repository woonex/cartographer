"""
IP-based rate limiter backed by DynamoDB.

Falls back to an in-memory store if DynamoDB is unavailable (e.g. local dev
without AWS credentials), so local development works without any extra setup.
"""

import time
from collections import defaultdict
from datetime import datetime, timezone

from settings_frontend import Settings


def _format_reset_time(reset_at: float) -> str:
    dt = datetime.fromtimestamp(reset_at, tz=timezone.utc)
    return dt.strftime("%H:%M UTC")


class _InMemoryStore:
    def __init__(self):
        self._data: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    def increment(self, ip: str, window_seconds: int) -> tuple[int, float]:
        count, window_start = self._data[ip]
        now = time.time()
        if now - window_start >= window_seconds:
            count, window_start = 0, now
        count += 1
        self._data[ip] = (count, window_start)
        return count, window_start + window_seconds


class _DynamoDBStore:
    def __init__(self, table: str, region: str):
        import boto3
        self._table = boto3.resource("dynamodb", region_name=region).Table(table)

    def increment(self, ip: str, window_seconds: int) -> tuple[int, float]:
        from boto3.dynamodb.conditions import Attr
        from botocore.exceptions import ClientError

        now = time.time()
        reset_at = now + window_seconds
        ttl = int(reset_at)

        try:
            resp = self._table.update_item(
                Key={"ip": ip},
                UpdateExpression=(
                    "SET #count = if_not_exists(#count, :zero) + :one, "
                    "#reset_at = if_not_exists(#reset_at, :reset), "
                    "#ttl = if_not_exists(#ttl, :ttl)"
                ),
                ConditionExpression=Attr("reset_at").not_exists() | Attr("reset_at").gt(now),
                ExpressionAttributeNames={
                    "#count": "count",
                    "#reset_at": "reset_at",
                    "#ttl": "ttl",
                },
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":one": 1,
                    ":reset": str(reset_at),
                    ":ttl": ttl,
                },
                ReturnValues="ALL_NEW",
            )
            attrs = resp["Attributes"]
            return int(attrs["count"]), float(attrs["reset_at"])
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Window expired between read and write — reset and retry once
                self._table.put_item(Item={
                    "ip": ip,
                    "count": 1,
                    "reset_at": str(reset_at),
                    "ttl": ttl,
                })
                return 1, reset_at
            raise


class RateLimiter:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._store = self._init_store()

    def _init_store(self):
        try:
            store = _DynamoDBStore(
                self._settings.dynamodb_table,
                self._settings.dynamodb_region,
            )
            # Probe to confirm credentials/table are reachable
            store._table.load()
            return store
        except Exception:
            print("DynamoDB unavailable — falling back to in-memory rate limit store", flush=True)
            return _InMemoryStore()

    def check(self, ip: str) -> tuple[bool, str]:
        """Returns (allowed, message). message is non-empty only when blocked."""
        if ip in self._settings.whitelist_ips:
            return True, ""

        window_seconds = self._settings.rate_limit_window_hours * 3600
        count, reset_at = self._store.increment(ip, window_seconds)

        if count > self._settings.rate_limit_requests:
            reset_str = _format_reset_time(reset_at)
            return False, (
                f"You've reached the daily request limit of {self._settings.rate_limit_requests}. "
                f"You can try again after {reset_str}."
            )
        return True, ""
