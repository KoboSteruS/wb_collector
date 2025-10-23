"""
Конфигурация логирования

Настройка loguru для централизованного логирования.
"""

import sys
from pathlib import Path
from loguru import logger

from .config import settings


def setup_logger() -> None:
    """
    Настройка логгера приложения.
    
    Конфигурирует loguru с выводом в консоль и файл.
    """
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Добавляем вывод в консоль с цветным форматированием (более детальный)
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="DEBUG",  # Показываем все уровни в консоли
        colorize=True,
    )
    
    # Создаем директорию для логов если не существует
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Добавляем вывод в файл с ротацией
    logger.add(
        settings.LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",  # Ротация при достижении 10 MB
        retention="30 days",  # Хранить логи 30 дней
        compression="zip",  # Сжимать старые логи
        enqueue=True,  # Асинхронная запись
    )
    
    logger.success(f"Логирование настроено. Уровень: {settings.LOG_LEVEL}")


# Инициализируем логгер при импорте модуля
setup_logger()

