from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vector_store_url: str
    embedding_model: str = "all-MiniLM-L6-v2"
    vehicle_library_url: str
    specifications_library_url: str
    collection_name: str = "manuals"
    top_k: int = 3
    min_similarity: float = 0.5

    model_config = {"env_prefix": "QUERY_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
