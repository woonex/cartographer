from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    query_url: str
    vehicle_library_url: str

    model_config = {"env_prefix": "FRONTEND_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
