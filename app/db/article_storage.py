"""
Хранилище для артикулов и результатов парсинга

Временное файловое хранилище.
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
from collections import Counter
from uuid import UUID

from app.models import Article, ParsingResult, ArticleAnalytics
from app.core import logger


class ArticleStorage:
    """Хранилище артикулов и результатов парсинга"""
    
    def __init__(
        self,
        articles_file: str = "data/articles.json",
        results_file: str = "data/parsing_results.json",
        analytics_file: str = "data/analytics.json"
    ):
        """Инициализация хранилища"""
        self.articles_file = Path(articles_file)
        self.results_file = Path(results_file)
        self.analytics_file = Path(analytics_file)
        
        for file in [self.articles_file, self.results_file, self.analytics_file]:
            file.parent.mkdir(parents=True, exist_ok=True)
            if not file.exists():
                self._save_json(file, {})
    
    def _load_json(self, file_path: Path) -> Dict:
        """Загрузка JSON"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки {file_path}: {e}")
            return {}
    
    def _save_json(self, file_path: Path, data: Dict) -> None:
        """Сохранение JSON"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения {file_path}: {e}")
    
    # === АРТИКУЛЫ ===
    
    def add_article(self, article: Article) -> bool:
        """Добавление артикула"""
        try:
            data = self._load_json(self.articles_file)
            article_id = article.article_id
            
            if article_id in data:
                logger.warning(f"⚠️ Артикул {article_id} уже существует")
                return False
            
            data[article_id] = article.to_dict()
            self._save_json(self.articles_file, data)
            logger.success(f"📦 Артикул {article_id} добавлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления артикула: {e}")
            return False
    
    def get_all_articles(self) -> List[Article]:
        """Получение всех артикулов"""
        try:
            data = self._load_json(self.articles_file)
            articles = []
            
            for article_data in data.values():
                article = Article(
                    article_id=article_data["article_id"],
                    name=article_data.get("name"),
                    brand=article_data.get("brand"),
                    uuid=UUID(article_data["uuid"])
                )
                articles.append(article)
            
            return articles
        except Exception as e:
            logger.error(f"Ошибка получения артикулов: {e}")
            return []
    
    # === РЕЗУЛЬТАТЫ ПАРСИНГА ===
    
    def add_parsing_result(self, result: ParsingResult) -> bool:
        """Добавление результата парсинга (перезаписывает старые данные)"""
        try:
            data = self._load_json(self.results_file)
            
            article_id = result.article_id
            account_uuid = result.account_uuid
            
            # Создаем структуру если не существует
            if article_id not in data:
                data[article_id] = {}
            
            # Перезаписываем результат для конкретного аккаунта
            data[article_id][account_uuid] = result.to_dict()
            self._save_json(self.results_file, data)
            logger.debug(f"💾 Результат парсинга для {article_id} (аккаунт {account_uuid[:8]}) сохранен")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения результата: {e}")
            return False
    
    def get_parsing_results(self, article_id: str) -> List[ParsingResult]:
        """Получение результатов парсинга для артикула"""
        try:
            data = self._load_json(self.results_file)
            results = []
            
            # Новая структура: article_id -> {account_uuid: result}
            article_data = data.get(article_id, {})
            
            for account_uuid, result_data in article_data.items():
                result = ParsingResult(
                    article_id=result_data["article_id"],
                    account_uuid=result_data["account_uuid"],
                    spp=result_data["spp"],
                    dest=result_data["dest"],
                    price_basic=result_data["price_basic"],
                    price_product=result_data["price_product"],
                    qty=result_data["qty"],
                    uuid=UUID(result_data["uuid"])
                )
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Ошибка получения результатов: {e}")
            return []
    
    # === АНАЛИТИКА ===
    
    def update_analytics(self, article_id: str) -> Optional[ArticleAnalytics]:
        """Обновление аналитики для артикула"""
        try:
            results = self.get_parsing_results(article_id)
            
            if not results:
                return None
            
            # Подсчитываем самые частые SPP и dest
            spp_counter = Counter([r.spp for r in results])
            dest_counter = Counter([r.dest for r in results])
            
            most_common_spp = spp_counter.most_common(1)[0][0]
            most_common_dest = dest_counter.most_common(1)[0][0]
            
            # Генерируем ссылку
            generated_url = self._generate_url(
                article_id,
                int(most_common_spp),
                most_common_dest
            )
            
            analytics = ArticleAnalytics(
                article_id=article_id,
                most_common_spp=most_common_spp,
                most_common_dest=most_common_dest,
                generated_url=generated_url,
                total_parses=len(results)
            )
            
            # Сохраняем аналитику
            data = self._load_json(self.analytics_file)
            data[article_id] = analytics.to_dict()
            self._save_json(self.analytics_file, data)
            
            logger.success(f"📊 Аналитика обновлена для {article_id}: SPP={most_common_spp}, dest={most_common_dest} (парсингов: {len(results)})")
            return analytics
            
        except Exception as e:
            logger.error(f"Ошибка обновления аналитики: {e}")
            return None
    
    def get_analytics(self, article_id: str) -> Optional[ArticleAnalytics]:
        """Получение аналитики для артикула"""
        try:
            data = self._load_json(self.analytics_file)
            
            if article_id not in data:
                return None
            
            analytics_data = data[article_id]
            return ArticleAnalytics(
                article_id=analytics_data["article_id"],
                most_common_spp=analytics_data["most_common_spp"],
                most_common_dest=analytics_data["most_common_dest"],
                generated_url=analytics_data["generated_url"],
                total_parses=analytics_data["total_parses"]
            )
        except Exception as e:
            logger.error(f"Ошибка получения аналитики: {e}")
            return None
    
    def _generate_url(self, article_id: str, spp: int, dest: str) -> str:
        """Генерация ссылки на товар"""
        base_url = "https://card.wb.ru/cards/v4/detail"
        return (
            f"{base_url}?appType=1&curr=rub&dest={dest}"
            f"&spp={spp}&hide_dtype=11&ab_testing=false"
            f"&lang=ru&nm={article_id}"
        )


# Глобальный экземпляр хранилища
article_storage = ArticleStorage()

