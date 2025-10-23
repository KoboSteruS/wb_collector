"""
Главный роутер API v1

Объединяет все endpoints версии 1.
"""

from fastapi import APIRouter

from app.core import logger
from .accounts import router as accounts_router
from .ws_routes import router as ws_router
from .articles import router as articles_router
from .proxies import router as proxies_router


# Создаем главный роутер для API v1
api_router = APIRouter()

# Подключаем роутеры модулей
api_router.include_router(accounts_router)
api_router.include_router(ws_router)
api_router.include_router(articles_router)
api_router.include_router(proxies_router)


@api_router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Проверка работоспособности приложения.
    
    Returns:
        dict: Статус приложения
    """
    logger.info("Health check endpoint вызван")
    return {
        "status": "ok",
        "message": "Приложение работает корректно"
    }


@api_router.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Корневой endpoint API.
    
    Returns:
        dict: Приветственное сообщение
    """
    return {
        "message": "WB_Collector API v1",
        "docs": "/docs",
        "redoc": "/redoc"
    }

