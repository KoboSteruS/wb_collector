"""
Главный модуль FastAPI приложения

Точка входа в приложение. Содержит настройку FastAPI и подключение роутеров.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.core import settings, logger
from app.api.v1 import api_router
from app.services.scheduler import parsing_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Управление жизненным циклом приложения.
    
    Выполняется при запуске и остановке приложения.
    
    Args:
        app: Экземпляр FastAPI приложения
        
    Yields:
        None
    """
    # Startup
    logger.info(f"Запуск приложения {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Режим отладки: {settings.DEBUG}")
    logger.info(f"Сервер запускается на {settings.HOST}:{settings.PORT}")
    
    # Запуск планировщика парсинга
    parsing_scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Остановка приложения")
    parsing_scheduler.shutdown()


def create_application() -> FastAPI:
    """
    Создание и настройка экземпляра FastAPI приложения.
    
    Returns:
        FastAPI: Настроенный экземпляр приложения
    """
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Профессиональное FastAPI приложение для работы с Wildberries API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )
    
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Подключение роутеров
    app.include_router(
        api_router,
        prefix="/api/v1"
    )
    
    # Главная страница - тестовый клиент
    @app.get("/", response_class=FileResponse)
    async def root():
        """Отдаем тестовый HTML клиент на главной странице"""
        html_file = Path("test_client.html")
        if html_file.exists():
            return FileResponse(html_file)
        return {"message": "Откройте test_client.html в браузере"}
    
    # Глобальный обработчик исключений
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception) -> JSONResponse:
        """
        Глобальный обработчик неперехваченных исключений.
        
        Args:
            request: HTTP запрос
            exc: Исключение
            
        Returns:
            JSONResponse: Ответ с информацией об ошибке
        """
        logger.error(f"Необработанное исключение: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Внутренняя ошибка сервера",
                "error": str(exc) if settings.DEBUG else "Internal Server Error"
            }
        )
    
    logger.info("FastAPI приложение успешно создано и настроено")
    return app


# Создание экземпляра приложения
app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

