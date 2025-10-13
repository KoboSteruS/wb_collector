"""
Core модуль приложения

Содержит базовые настройки, конфигурацию и логирование.
"""

from .config import settings
from .logger import logger

__all__ = ["settings", "logger"]

