"""
Модуль работы с базой данных

Содержит настройки подключения и сессий БД.
"""

from .storage import account_storage, AccountStorage
from .article_storage import article_storage, ArticleStorage

__all__ = ["account_storage", "AccountStorage", "article_storage", "ArticleStorage"]

