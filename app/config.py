import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Syllabus QA"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 1

    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    REDIS_URL: str

    UPLOAD_FOLDER: str = "./uploads"

    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None

    OPENAI_MODEL_NAME: str = "gpt-4o"
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"
    
    GEMINI_EMBEDDING_MODEL_NAME: str = "models/text-embedding-005"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()


os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)