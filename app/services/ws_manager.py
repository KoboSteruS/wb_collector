"""
Менеджер WebSocket соединений

Управление активными WebSocket сессиями для авторизации.
"""

import asyncio
from typing import Dict, Optional
from uuid import uuid4
from fastapi import WebSocket

from app.core import logger


class AuthSession:
    """
    Сессия авторизации через WebSocket.
    
    Attributes:
        session_id: Уникальный идентификатор сессии
        websocket: WebSocket соединение
        phone: Номер телефона
        name: Название аккаунта
        code_event: Event для ожидания кода от пользователя
        code: Код подтверждения от пользователя
    """
    
    def __init__(self, websocket: WebSocket, phone: str, name: str):
        """
        Инициализация сессии.
        
        Args:
            websocket: WebSocket соединение
            phone: Номер телефона
            name: Название аккаунта
        """
        self.session_id = str(uuid4())
        self.websocket = websocket
        self.phone = phone
        self.name = name
        self.code_event = asyncio.Event()
        self.code: Optional[str] = None
    
    async def send_message(self, message_type: str, data: dict) -> None:
        """
        Отправка сообщения через WebSocket.
        
        Args:
            message_type: Тип сообщения
            data: Данные сообщения
        """
        try:
            await self.websocket.send_json({
                "type": message_type,
                "data": data
            })
            logger.debug(f"Сообщение отправлено: {message_type}")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
    
    async def wait_for_code(self, timeout: int = 300) -> Optional[str]:
        """
        Ожидание кода от пользователя.
        
        Args:
            timeout: Таймаут ожидания в секундах
            
        Returns:
            Optional[str]: Код или None при таймауте
        """
        try:
            await asyncio.wait_for(self.code_event.wait(), timeout=timeout)
            return self.code
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут ожидания кода для сессии {self.session_id}")
            return None
    
    def set_code(self, code: str) -> None:
        """
        Установка кода от пользователя.
        
        Args:
            code: Код подтверждения
        """
        self.code = code
        self.code_event.set()
        logger.info(f"Код получен для сессии {self.session_id}")


class WebSocketManager:
    """
    Менеджер WebSocket соединений.
    
    Управляет активными сессиями авторизации.
    """
    
    def __init__(self):
        """Инициализация менеджера."""
        self.active_sessions: Dict[str, AuthSession] = {}
    
    def create_session(
        self,
        websocket: WebSocket,
        phone: str,
        name: str
    ) -> AuthSession:
        """
        Создание новой сессии авторизации.
        
        Args:
            websocket: WebSocket соединение
            phone: Номер телефона
            name: Название аккаунта
            
        Returns:
            AuthSession: Созданная сессия
        """
        session = AuthSession(websocket, phone, name)
        self.active_sessions[session.session_id] = session
        logger.info(f"Создана сессия {session.session_id} для {name}")
        return session
    
    def get_session(self, session_id: str) -> Optional[AuthSession]:
        """
        Получение сессии по ID.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Optional[AuthSession]: Сессия или None
        """
        return self.active_sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> None:
        """
        Удаление сессии.
        
        Args:
            session_id: ID сессии
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Сессия {session_id} удалена")
    
    async def close_session(self, session_id: str) -> None:
        """
        Закрытие и удаление сессии.
        
        Args:
            session_id: ID сессии
        """
        session = self.get_session(session_id)
        if session:
            try:
                await session.websocket.close()
            except:
                pass
            self.remove_session(session_id)


# Глобальный экземпляр менеджера
ws_manager = WebSocketManager()


