from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vector_store_url: str
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50

    model_config = {"env_prefix": "INGESTION_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
