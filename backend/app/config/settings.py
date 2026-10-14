from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'),
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # Gemini
    gemini_api_key: str = Field(default='', alias='GEMINI_API_KEY')
    gemini_text_model: str = Field(default='gemini-2.0-flash', alias='GEMINI_TEXT_MODEL')
    gemini_tts_model: str = Field(default='gemini-2.5-flash-preview-tts', alias='GEMINI_TTS_MODEL')

    # Database
    database_url: str = Field(default='sqlite:///./data/speech_analytics.db', alias='DATABASE_URL')

    # File storage
    upload_dir: str = Field(default='./uploads', alias='UPLOAD_DIR')
    generated_dir: str = Field(default='./generated', alias='GENERATED_DIR')
    max_file_size_mb: int = Field(default=500, alias='MAX_FILE_SIZE_MB')

    # CORS
    cors_origins: List[str] = Field(
        default=['http://localhost:5173', 'http://localhost:3000'],
        alias='CORS_ORIGINS'
    )


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
