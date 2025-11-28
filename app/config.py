"""
Конфигурация приложения Sales Scout
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""

    # Bitrix24
    BITRIX24_WEBHOOK_URL: str
    BITRIX24_BOT_ID: str = ""
    BITRIX24_CLIENT_ID: str = "9dqwph499ep9cpqdkyd1q2zxjvchddox"

    # DaData
    DADATA_API_KEY: str

    # OpenRouter (для Perplexity и LLM анализа)
    OPENROUTER_API_KEY: str
    DEFAULT_MODEL: str = "anthropic/claude-3.5-sonnet"
    PERPLEXITY_MODEL: str = "perplexity/sonar-pro"

    # Описание продукта
    OUR_PRODUCT_DESCRIPTION: str = "CRM система для автоматизации продаж"

    # Настройки приложения
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
