import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Document Intelligence Engine"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/doc_intelligence"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/doc_intelligence"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM Provider: "ollama" (localhosted Qwen) or "groq"
    LLM_PROVIDER: str = "ollama"

    # Local Ollama (Primary: Qwen on GTX 1650)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"

    # Groq API (Cloud Engine)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    
    # Embedding Model
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384
    
    # Storage & Uploads
    UPLOAD_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../uploads"))
    MAX_FILE_SIZE_MB: int = 50
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000"]
    
    model_config = SettingsConfigDict(
        env_file=[os.path.join(os.path.dirname(__file__), "../../../.env"), ".env", "../.env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
