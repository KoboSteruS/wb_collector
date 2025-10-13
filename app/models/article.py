"""
Модель артикула для парсинга

Хранит информацию об артикулах и результатах парсинга.
"""

from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4


class Article:
    """
    Модель артикула для парсинга.
    
    Attributes:
        uuid: Уникальный идентификатор
        article_id: ID артикула WB
        name: Название товара
        brand: Бренд
        created_at: Дата создания
        updated_at: Дата последнего парсинга
    """
    
    def __init__(
        self,
        article_id: str,
        name: Optional[str] = None,
        brand: Optional[str] = None,
        uuid: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """Инициализация артикула"""
        self.uuid = uuid or uuid4()
        self.article_id = article_id
        self.name = name
        self.brand = brand
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "uuid": str(self.uuid),
            "article_id": self.article_id,
            "name": self.name,
            "brand": self.brand,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ParsingResult:
    """
    Результат парсинга артикула.
    
    Attributes:
        uuid: Уникальный идентификатор
        article_id: ID артикула
        account_uuid: UUID аккаунта
        spp: SPP значение
        dest: Dest значение
        price_basic: Базовая цена
        price_product: Цена со скидкой
        qty: Остаток
        parsed_at: Время парсинга
    """
    
    def __init__(
        self,
        article_id: str,
        account_uuid: str,
        spp: float,
        dest: str,
        price_basic: int,
        price_product: int,
        qty: int,
        uuid: Optional[UUID] = None,
        parsed_at: Optional[datetime] = None
    ):
        """Инициализация результата парсинга"""
        self.uuid = uuid or uuid4()
        self.article_id = article_id
        self.account_uuid = account_uuid
        self.spp = spp
        self.dest = dest
        self.price_basic = price_basic
        self.price_product = price_product
        self.qty = qty
        self.parsed_at = parsed_at or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "uuid": str(self.uuid),
            "article_id": self.article_id,
            "account_uuid": self.account_uuid,
            "spp": self.spp,
            "dest": self.dest,
            "price_basic": self.price_basic,
            "price_product": self.price_product,
            "qty": self.qty,
            "parsed_at": self.parsed_at.isoformat() if self.parsed_at else None
        }


class ArticleAnalytics:
    """
    Аналитика по артикулу.
    
    Attributes:
        article_id: ID артикула
        most_common_spp: Самый частый SPP
        most_common_dest: Самый частый dest
        generated_url: Сгенерированная ссылка
        total_parses: Количество парсингов
        last_updated: Последнее обновление
    """
    
    def __init__(
        self,
        article_id: str,
        most_common_spp: float,
        most_common_dest: str,
        generated_url: str,
        total_parses: int = 0,
        last_updated: Optional[datetime] = None
    ):
        """Инициализация аналитики"""
        self.article_id = article_id
        self.most_common_spp = most_common_spp
        self.most_common_dest = most_common_dest
        self.generated_url = generated_url
        self.total_parses = total_parses
        self.last_updated = last_updated or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "article_id": self.article_id,
            "most_common_spp": self.most_common_spp,
            "most_common_dest": self.most_common_dest,
            "generated_url": self.generated_url,
            "total_parses": self.total_parses,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }

