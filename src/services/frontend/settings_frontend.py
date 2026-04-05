from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    query_url: str
    vehicle_library_url: str
    rate_limit_requests: int = 30
    rate_limit_window_hours: int = 24
    rate_limit_whitelist: str = ""  # comma-separated IPs, e.g. "1.2.3.4,5.6.7.8"
    dynamodb_table: str = "cartographer-rate-limits"
    dynamodb_region: str = "us-east-1"

    model_config = {"env_prefix": "FRONTEND_"}

    @property
    def whitelist_ips(self) -> set[str]:
        return {ip.strip() for ip in self.rate_limit_whitelist.split(",") if ip.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
