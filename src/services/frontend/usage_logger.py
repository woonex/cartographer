"""
Per-query usage logging to DynamoDB.

Writes one item per completed query: username (hash key), timestamp (range key), vehicle.
Query text is intentionally not logged.

Falls back to a no-op if DynamoDB is unavailable (e.g. local dev).
"""

from datetime import datetime, timezone

from settings_frontend import Settings


class _NoOpLogger:
    def log(self, username: str, vehicle: str) -> None:
        pass


class _DynamoDBLogger:
    def __init__(self, table: str, region: str):
        import boto3
        self._table = boto3.resource("dynamodb", region_name=region).Table(table)

    def log(self, username: str, vehicle: str) -> None:
        self._table.put_item(Item={
            "username": username,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "vehicle": vehicle,
        })


class UsageLogger:
    def __init__(self, settings: Settings):
        self._logger = self._init_logger(settings)

    def _init_logger(self, settings: Settings):
        try:
            logger = _DynamoDBLogger(settings.usage_log_table, settings.dynamodb_region)
            logger._table.load()
            return logger
        except Exception:
            print("Usage log DynamoDB table unavailable — logging disabled", flush=True)
            return _NoOpLogger()

    def log(self, username: str, vehicle: str) -> None:
        try:
            self._logger.log(username, vehicle)
        except Exception as e:
            print(f"Usage log write failed: {e}", flush=True)
