"""
Модели данных

Содержит модели для работы с базой данных.
"""

from .base import BaseModel
from .account import Account
from .article import Article, ParsingResult, ArticleAnalytics

__all__ = ["BaseModel", "Account", "Article", "ParsingResult", "ArticleAnalytics"]

