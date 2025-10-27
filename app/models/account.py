"""
Модель аккаунта Wildberries

Хранит информацию об аккаунтах WB и их cookies.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class Account:
    """
    Модель аккаунта Wildberries.
    
    Attributes:
        uuid: Уникальный идентификатор аккаунта
        name: Название аккаунта для различия
        phone: Номер телефона (без +7)
        cookies: JSON строка с cookies
        proxy_uuid: UUID привязанного прокси
        created_at: Дата создания
        updated_at: Дата последнего обновления
    """
    
    def __init__(
        self,
        name: str,
        phone: str,
        cookies: Optional[str] = None,
        proxy_uuid: Optional[str] = None,
        uuid: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """
        Инициализация аккаунта.
        
        Args:
            name: Название аккаунта
            phone: Номер телефона
            cookies: JSON строка с cookies
            proxy_uuid: UUID привязанного прокси
            uuid: UUID аккаунта
            created_at: Дата создания
            updated_at: Дата обновления
        """
        self.uuid = uuid or uuid4()
        self.name = name
        self.phone = phone
        self.cookies = cookies
        self.proxy_uuid = proxy_uuid
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
    
    def update_cookies(self, cookies: str) -> None:
        """
        Обновление cookies аккаунта.
        
        Args:
            cookies: Новые cookies в формате JSON
        """
        self.cookies = cookies
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """
        Преобразование модели в словарь.
        
        Returns:
            dict: Словарь с данными аккаунта
        """
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "phone": self.phone,
            "cookies": self.cookies,
            "proxy_uuid": self.proxy_uuid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

