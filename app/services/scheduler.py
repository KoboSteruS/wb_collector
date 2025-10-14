"""
Планировщик фоновых задач

Управление периодическими задачами парсинга.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core import logger, settings
from .wb_parser import wb_parser


class ParsingScheduler:
    """Планировщик для парсинга"""
    
    def __init__(self):
        """Инициализация планировщика"""
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self) -> None:
        """Настройка задач"""
        if not settings.PARSING_ENABLED:
            logger.info("⚠️ Фоновый парсинг отключен в настройках")
            return
        
        # Добавляем задачу парсинга - каждые 2 часа
        self.scheduler.add_job(
            self._run_parsing,
            IntervalTrigger(hours=2),
            id="wb_parsing",
            name="Парсинг WB артикулов",
            replace_existing=True
        )
        
        logger.success("📅 Парсинг запланирован каждые 2 часа")
    
    async def _run_parsing(self) -> None:
        """Запуск парсинга"""
        logger.info("⏰ Запуск запланированного парсинга...")
        try:
            # Запускаем парсинг в отдельном потоке
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, wb_parser.parse_all_articles)
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге: {e}")
    
    def start(self) -> None:
        """Запуск планировщика"""
        if settings.PARSING_ENABLED:
            self.scheduler.start()
            logger.success("✅ Планировщик парсинга запущен")
        else:
            logger.info("ℹ️ Планировщик не запущен (отключен в настройках)")
    
    def shutdown(self) -> None:
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("🛑 Планировщик остановлен")
    
    async def run_now(self) -> int:
        """Запустить парсинг немедленно"""
        logger.info("🚀 Запуск парсинга по требованию...")
        return await self._run_parsing()


# Глобальный экземпляр планировщика
parsing_scheduler = ParsingScheduler()

