"""
Базовая модель для всех моделей БД

Содержит общие поля: uuid, created_at, updated_at.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class BaseModel:
    """
    Базовая модель для всех моделей БД.
    
    Содержит стандартные поля, которые должны быть у всех моделей:
    - uuid: Уникальный идентификатор
    - created_at: Дата и время создания
    - updated_at: Дата и время последнего обновления
    
    Note:
        Это заготовка для будущей интеграции с ORM (SQLAlchemy, Tortoise и т.д.)
    """
    
    uuid: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    def __init__(self):
        """Инициализация базовой модели"""
        self.uuid = uuid4()
        self.created_at = datetime.utcnow()
        self.updated_at = None
    
    def update_timestamp(self) -> None:
        """Обновление временной метки"""
        self.updated_at = datetime.utcnow()

