"""
Pydantic схемы для артикулов

Схемы для валидации запросов и ответов API.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ArticleCreate(BaseModel):
    """Схема для создания артикула"""
    
    article_id: str = Field(
        ...,
        description="ID артикула WB",
        examples=["15526304"]
    )


class ArticleResponse(BaseModel):
    """Схема ответа с информацией об артикуле"""
    
    uuid: str = Field(..., description="UUID артикула")
    article_id: str = Field(..., description="ID артикула WB")
    name: Optional[str] = Field(None, description="Название товара")
    brand: Optional[str] = Field(None, description="Бренд")
    created_at: Optional[str] = Field(None, description="Дата создания")
    updated_at: Optional[str] = Field(None, description="Дата обновления")


class LinkResponse(BaseModel):
    """Схема ответа с сгенерированной ссылкой"""
    
    article_id: str = Field(..., description="ID артикула")
    generated_url: str = Field(..., description="Сгенерированная ссылка")
    most_common_spp: float = Field(..., description="Самый частый SPP")
    most_common_dest: str = Field(..., description="Самый частый dest")
    total_parses: int = Field(..., description="Количество парсингов")
    last_updated: Optional[str] = Field(None, description="Последнее обновление")


class ParsingStatus(BaseModel):
    """Статус парсинга"""
    
    status: str = Field(..., description="Статус операции")
    message: str = Field(..., description="Сообщение")
    total_parsed: Optional[int] = Field(None, description="Количество обработанных")

