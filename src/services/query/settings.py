from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vector_store_url: str
    collection_name: str = "manuals"
    top_k: int = 3
    min_similarity: float = 0.75

    model_config = {"env_prefix": "QUERY_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
