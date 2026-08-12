from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    auth_service_url: str = "http://auth_service:8001"
    processing_service_url: str = "http://data_processing_engine:8002"
    request_timeout_seconds: float = 10.0

    class Config:
        env_file = ".env"
        env_prefix = ""
        extra = "ignore"

settings = Settings()
