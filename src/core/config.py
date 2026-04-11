from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    PROJECT_NAME: str = "HR Data Parser API"
    VLLM_NGROK_URL: str

@lru_cache
def get_config() -> Settings:
    return Settings()