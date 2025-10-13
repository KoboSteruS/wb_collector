"""
Сервисный слой

Содержит бизнес-логику приложения.
"""

from .wb_auth import WBAuthService
from .ws_manager import ws_manager, WebSocketManager, AuthSession
from .wb_parser import wb_parser, WBParserService

__all__ = [
    "WBAuthService",
    "ws_manager",
    "WebSocketManager",
    "AuthSession",
    "wb_parser",
    "WBParserService"
]

