"""
Конфигурация приложения

Централизованное управление настройками через переменные окружения.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Класс настроек приложения.
    
    Все настройки загружаются из переменных окружения или .env файла.
    """
    
    # Основные настройки приложения
    APP_NAME: str = Field(default="WB_Collector", description="Название приложения")
    APP_VERSION: str = Field(default="0.1.0", description="Версия приложения")
    DEBUG: bool = Field(default=False, description="Режим отладки")
    
    # Настройки сервера
    HOST: str = Field(default="0.0.0.0", description="Хост для запуска сервера")
    PORT: int = Field(default=8000, description="Порт для запуска сервера")
    
    # Настройки базы данных
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="URL подключения к базе данных"
    )
    
    # Настройки безопасности
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Секретный ключ для JWT"
    )
    ALGORITHM: str = Field(default="HS256", description="Алгоритм шифрования JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Время жизни access токена в минутах"
    )
    
    # CORS настройки
    CORS_ORIGINS: list[str] = Field(
        default=["*"],
        description="Разрешенные CORS origins"
    )
    
    # Настройки логирования
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")
    LOG_FILE: str = Field(default="logs/app.log", description="Путь к файлу логов")
    
    # Настройки парсинга
    PARSING_ENABLED: bool = Field(default=True, description="Включить фоновый парсинг")
    PARSING_SCHEDULE_HOUR: int = Field(default=12, description="Час запуска парсинга (0-23)")
    PARSING_SCHEDULE_MINUTE: int = Field(default=0, description="Минута запуска парсинга (0-59)")
    PARSING_HEADLESS: bool = Field(default=True, description="Запуск браузера в headless режиме")
    
    class Config:
        """Конфигурация Pydantic Settings"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Глобальный экземпляр настроек
settings = Settings()

