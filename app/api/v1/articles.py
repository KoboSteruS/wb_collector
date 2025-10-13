"""
API endpoints для работы с артикулами

Endpoints для добавления артикулов и получения сгенерированных ссылок.
"""

from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas import ArticleCreate, ArticleResponse, LinkResponse, ParsingStatus
from app.models import Article
from app.db import article_storage
from app.services.scheduler import parsing_scheduler
from app.core import logger


router = APIRouter(prefix="/articles", tags=["Articles"])


@router.post("/add", response_model=ArticleResponse)
async def add_article(article_data: ArticleCreate) -> ArticleResponse:
    """
    Добавление нового артикула для парсинга.
    
    Args:
        article_data: Данные артикула (ID)
        
    Returns:
        ArticleResponse: Информация о созданном артикуле
        
    Raises:
        HTTPException: При ошибках
    """
    logger.info(f"Получен запрос на добавление артикула: {article_data.article_id}")
    
    # Создание артикула
    article = Article(article_id=article_data.article_id)
    
    # Сохранение в БД
    if not article_storage.add_article(article):
        raise HTTPException(
            status_code=400,
            detail=f"Артикул {article_data.article_id} уже существует"
        )
    
    return ArticleResponse(
        uuid=str(article.uuid),
        article_id=article.article_id,
        name=article.name,
        brand=article.brand,
        created_at=article.created_at.isoformat() if article.created_at else None,
        updated_at=article.updated_at.isoformat() if article.updated_at else None
    )


@router.get("/list", response_model=List[ArticleResponse])
async def list_articles() -> List[ArticleResponse]:
    """
    Получение списка всех артикулов.
    
    Returns:
        List[ArticleResponse]: Список артикулов
    """
    logger.info("Запрос списка артикулов")
    
    articles = article_storage.get_all_articles()
    
    return [
        ArticleResponse(
            uuid=str(article.uuid),
            article_id=article.article_id,
            name=article.name,
            brand=article.brand,
            created_at=article.created_at.isoformat() if article.created_at else None,
            updated_at=article.updated_at.isoformat() if article.updated_at else None
        )
        for article in articles
    ]


@router.get("/{article_id}/link", response_model=LinkResponse)
async def get_article_link(article_id: str) -> LinkResponse:
    """
    Получение сгенерированной ссылки для артикула.
    
    Возвращает ссылку с самыми частыми SPP и dest на основе аналитики.
    
    Args:
        article_id: ID артикула WB
        
    Returns:
        LinkResponse: Сгенерированная ссылка и статистика
        
    Raises:
        HTTPException: Если артикул не найден или нет данных
    """
    logger.info(f"Запрос ссылки для артикула {article_id}")
    
    # Получаем аналитику
    analytics = article_storage.get_analytics(article_id)
    
    if not analytics:
        raise HTTPException(
            status_code=404,
            detail=f"Нет данных для артикула {article_id}. Запустите парсинг или дождитесь планового."
        )
    
    return LinkResponse(
        article_id=analytics.article_id,
        generated_url=analytics.generated_url,
        most_common_spp=analytics.most_common_spp,
        most_common_dest=analytics.most_common_dest,
        total_parses=analytics.total_parses,
        last_updated=analytics.last_updated.isoformat() if analytics.last_updated else None
    )


@router.post("/parse/now", response_model=ParsingStatus)
async def parse_now() -> ParsingStatus:
    """
    Запустить парсинг немедленно (вне расписания).
    
    Returns:
        ParsingStatus: Статус выполнения
    """
    logger.info("🚀 Запуск парсинга по требованию...")
    
    try:
        total_parsed = await parsing_scheduler.run_now()
        
        return ParsingStatus(
            status="success",
            message=f"Парсинг завершен успешно",
            total_parsed=total_parsed
        )
    except Exception as e:
        logger.error(f"Ошибка парсинга: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при парсинге: {str(e)}"
        )


@router.get("/schedule/status")
async def get_schedule_status() -> dict:
    """
    Получение информации о расписании парсинга.
    
    Returns:
        dict: Информация о настройках планировщика
    """
    from app.core import settings
    
    return {
        "enabled": settings.PARSING_ENABLED,
        "schedule_hour": settings.PARSING_SCHEDULE_HOUR,
        "schedule_minute": settings.PARSING_SCHEDULE_MINUTE,
        "headless": settings.PARSING_HEADLESS,
        "schedule_description": f"Запуск каждый день в {settings.PARSING_SCHEDULE_HOUR:02d}:{settings.PARSING_SCHEDULE_MINUTE:02d}"
    }

