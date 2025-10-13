"""
Pydantic схемы

Содержит схемы для валидации и сериализации данных API.
"""

from .account import AccountCreate, AccountResponse, LoginStatus
from .article import ArticleCreate, ArticleResponse, LinkResponse, ParsingStatus

__all__ = [
    "AccountCreate",
    "AccountResponse",
    "LoginStatus",
    "ArticleCreate",
    "ArticleResponse",
    "LinkResponse",
    "ParsingStatus"
]

