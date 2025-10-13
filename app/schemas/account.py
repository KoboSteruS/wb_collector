"""
Pydantic схемы для аккаунтов

Схемы для валидации запросов и ответов API.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AccountCreate(BaseModel):
    """
    Схема для создания нового аккаунта.
    """
    
    name: str = Field(
        ...,
        description="Название аккаунта для различия",
        min_length=1,
        max_length=100,
        examples=["Основной аккаунт", "Тестовый"]
    )
    
    phone: str = Field(
        ...,
        description="Номер телефона без +7 (только цифры)",
        pattern=r"^\d{10}$",
        examples=["9522675444"]
    )
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """
        Валидация номера телефона.
        
        Args:
            v: Номер телефона
            
        Returns:
            str: Валидированный номер
            
        Raises:
            ValueError: Если номер некорректен
        """
        if not v.isdigit():
            raise ValueError("Номер должен содержать только цифры")
        if len(v) != 10:
            raise ValueError("Номер должен содержать 10 цифр (без +7)")
        return v


class AccountResponse(BaseModel):
    """
    Схема ответа с информацией об аккаунте.
    """
    
    uuid: str = Field(..., description="Уникальный идентификатор аккаунта")
    name: str = Field(..., description="Название аккаунта")
    phone: str = Field(..., description="Номер телефона")
    has_cookies: bool = Field(..., description="Наличие сохраненных cookies")
    created_at: Optional[str] = Field(None, description="Дата создания")
    updated_at: Optional[str] = Field(None, description="Дата обновления")


class LoginStatus(BaseModel):
    """
    Схема статуса авторизации.
    """
    
    status: str = Field(..., description="Статус операции")
    message: str = Field(..., description="Сообщение")
    account_uuid: Optional[str] = Field(None, description="UUID созданного аккаунта")

