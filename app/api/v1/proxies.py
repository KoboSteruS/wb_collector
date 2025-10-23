"""
API для управления прокси
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger

from app.db.proxy_storage import ProxyStorage

router = APIRouter(prefix="/proxies", tags=["proxies"])

# Инициализация хранилища прокси
proxy_storage = ProxyStorage()


class ProxyCreate(BaseModel):
    """Схема для создания прокси"""
    name: str = Field(..., description="Название прокси")
    host: str = Field(..., description="Хост прокси")
    port: int = Field(..., ge=1, le=65535, description="Порт прокси")
    username: Optional[str] = Field(None, description="Логин прокси")
    password: Optional[str] = Field(None, description="Пароль прокси")


class ProxyResponse(BaseModel):
    """Схема ответа с данными прокси"""
    uuid: str = Field(..., description="UUID прокси")
    name: str = Field(..., description="Название прокси")
    host: str = Field(..., description="Хост прокси")
    port: int = Field(..., description="Порт прокси")
    username: Optional[str] = Field(None, description="Логин прокси")
    status: str = Field(..., description="Статус прокси")


@router.post("/add", response_model=dict)
async def add_proxy(proxy_data: ProxyCreate):
    """
    Добавляет новый прокси
    
    Args:
        proxy_data: Данные прокси
        
    Returns:
        Результат добавления
    """
    try:
        logger.info(f"🌐 Добавление прокси: {proxy_data.name} ({proxy_data.host}:{proxy_data.port})")
        
        # Проверяем уникальность имени
        existing_proxies = proxy_storage.get_all_proxies()
        for proxy in existing_proxies:
            if proxy['name'] == proxy_data.name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Прокси с именем '{proxy_data.name}' уже существует"
                )
        
        # Добавляем прокси
        proxy_uuid = proxy_storage.add_proxy(
            name=proxy_data.name,
            host=proxy_data.host,
            port=proxy_data.port,
            username=proxy_data.username,
            password=proxy_data.password
        )
        
        logger.success(f"✅ Прокси '{proxy_data.name}' добавлен с UUID: {proxy_uuid}")
        
        return {
            "success": True,
            "message": f"Прокси '{proxy_data.name}' успешно добавлен",
            "proxy_uuid": proxy_uuid
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка добавления прокси: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка добавления прокси: {str(e)}"
        )


@router.get("/list", response_model=List[ProxyResponse])
async def list_proxies():
    """
    Получает список всех прокси
    
    Returns:
        Список прокси
    """
    try:
        logger.debug("Запрос списка прокси")
        
        proxies = proxy_storage.get_all_proxies()
        
        # Преобразуем в формат ответа (без паролей)
        response_proxies = []
        for proxy in proxies:
            response_proxies.append(ProxyResponse(
                uuid=proxy['uuid'],
                name=proxy['name'],
                host=proxy['host'],
                port=proxy['port'],
                username=proxy.get('username'),
                status=proxy.get('status', 'unknown')
            ))
        
        logger.debug(f"Возвращено {len(response_proxies)} прокси")
        return response_proxies
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка прокси: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения списка прокси: {str(e)}"
        )


@router.get("/{proxy_uuid}", response_model=ProxyResponse)
async def get_proxy(proxy_uuid: str):
    """
    Получает прокси по UUID
    
    Args:
        proxy_uuid: UUID прокси
        
    Returns:
        Данные прокси
    """
    try:
        logger.debug(f"🔍 Запрос прокси: {proxy_uuid}")
        
        proxy = proxy_storage.get_proxy(proxy_uuid)
        
        if not proxy:
            raise HTTPException(
                status_code=404,
                detail=f"Прокси с UUID {proxy_uuid} не найден"
            )
        
        return ProxyResponse(
            uuid=proxy['uuid'],
            name=proxy['name'],
            host=proxy['host'],
            port=proxy['port'],
            username=proxy.get('username'),
            status=proxy.get('status', 'unknown')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения прокси {proxy_uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения прокси: {str(e)}"
        )


@router.delete("/delete/{proxy_uuid}")
async def delete_proxy(proxy_uuid: str):
    """
    Удаляет прокси
    
    Args:
        proxy_uuid: UUID прокси
        
    Returns:
        Результат удаления
    """
    try:
        logger.info(f"🗑️ Удаление прокси: {proxy_uuid}")
        
        success = proxy_storage.delete_proxy(proxy_uuid)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Прокси с UUID {proxy_uuid} не найден"
            )
        
        logger.success(f"✅ Прокси {proxy_uuid} удален")
        
        return {
            "success": True,
            "message": f"Прокси {proxy_uuid} успешно удален"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка удаления прокси {proxy_uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления прокси: {str(e)}"
        )


@router.get("/available/list", response_model=List[ProxyResponse])
async def get_available_proxies():
    """
    Получает список доступных прокси
    
    Returns:
        Список доступных прокси
    """
    try:
        logger.debug("Запрос доступных прокси")
        
        available_proxies = proxy_storage.get_available_proxies()
        
        # Преобразуем в формат ответа
        response_proxies = []
        for proxy in available_proxies:
            response_proxies.append(ProxyResponse(
                uuid=proxy['uuid'],
                name=proxy['name'],
                host=proxy['host'],
                port=proxy['port'],
                username=proxy.get('username'),
                status=proxy.get('status', 'active')
            ))
        
        logger.debug(f"Возвращено {len(response_proxies)} доступных прокси")
        return response_proxies
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения доступных прокси: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения доступных прокси: {str(e)}"
        )
