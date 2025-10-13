"""
Скрипт запуска приложения

Упрощенный способ запуска FastAPI приложения.
"""

import uvicorn

from app.core import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

