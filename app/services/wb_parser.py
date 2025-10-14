"""
Сервис парсинга Wildberries

Парсинг SPP и аналитика по артикулам.
"""

import json
import gzip
import time
import tempfile
from io import BytesIO
from urllib.parse import urlparse, parse_qs
from typing import Optional, List, Dict
from uuid import uuid4

from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options

from app.core import logger, settings
from app.db import account_storage, article_storage
from app.models import ParsingResult


class WBParserService:
    """Сервис для парсинга данных с Wildberries"""
    
    def __init__(self, headless: bool = True):
        """Инициализация сервиса"""
        self.headless = headless
    
    def _extract_prices_and_stocks(
        self,
        json_bytes: bytes,
        target_id: Optional[str] = None
    ) -> List[Dict]:
        """Извлечение данных из ответа API"""
        try:
            # Распаковка gzip если нужно
            if json_bytes[:2] == b"\x1f\x8b":
                json_bytes = gzip.GzipFile(fileobj=BytesIO(json_bytes)).read()
            
            text = json_bytes.decode("utf-8", errors="ignore")
            data = json.loads(text)
            result = []
            
            for product in data.get("products", []):
                if target_id and str(product.get("id")) != str(target_id):
                    continue
                
                id_ = product.get("id")
                brand = product.get("brand")
                name = product.get("name")
                
                total_qty = 0
                price_basic = None
                price_product = None
                
                for size in product.get("sizes", []):
                    if not price_basic:
                        price_basic = size.get("price", {}).get("basic")
                        price_product = size.get("price", {}).get("product")
                    for stock in size.get("stocks", []):
                        total_qty += stock.get("qty", 0)
                
                result.append({
                    "id": id_,
                    "brand": brand,
                    "name": name,
                    "qty": total_qty,
                    "price_basic": price_basic,
                    "price_product": price_product,
                })
            
            return result
            
        except Exception as e:
            logger.warning(f"Ошибка парсинга JSON: {e}")
            return []
    
    def parse_article(
        self,
        article_id: str,
        account_uuid: str,
        cookies: str
    ) -> Optional[ParsingResult]:
        """
        Парсинг одного артикула с использованием cookies аккаунта.
        
        Args:
            article_id: ID артикула WB
            account_uuid: UUID аккаунта
            cookies: JSON строка с cookies
            
        Returns:
            Optional[ParsingResult]: Результат парсинга или None
        """
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        
        # Флаги для работы без GPU (Ubuntu сервер)
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-setuid-sandbox")
        
        # Остальные флаги
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-default-apps")
        
        # Используем ChromeDriver без явного указания binary_location
        from selenium.webdriver.chrome.service import Service
        
        chromedriver_path = '/usr/bin/chromedriver'
        logger.info(f"🚀 Запуск парсера через ChromeDriver: {chromedriver_path}")
        
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.scopes = ['.*u-card.wb.ru/cards/v4/detail.*']
        
        try:
            logger.info(f"🔍 Парсинг артикула {article_id} через аккаунт {account_uuid[:8]}...")
            
            # Загружаем главную страницу
            driver.get("https://www.wildberries.ru/")
            
            # Применяем cookies
            cookies_list = json.loads(cookies)
            for cookie in cookies_list:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            
            logger.debug(f"Cookies применены для {article_id}")
            
            # Открываем страницу товара
            product_url = f"https://www.wildberries.ru/catalog/{article_id}/detail.aspx"
            driver.get(product_url)
            time.sleep(5)  # Ждем загрузки и API запросов
            
            # Собираем цены с картой WB с HTML
            price_with_card = None
            card_discount_percent = None
            
            try:
                # Цена с картой WB (красная)
                card_price_element = driver.find_element("css selector", "span.priceBlockWalletPrice--RJGuT")
                card_price_text = card_price_element.text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                price_with_card = int(card_price_text)
                logger.debug(f"💳 Цена с картой WB: {price_with_card} ₽")
            except Exception as e:
                logger.debug(f"Цена с картой WB не найдена: {e}")
            
            try:
                # Пробуем разные селекторы для основной цены
                base_price_selectors = [
                    "ins.price-block__final-price",
                    ".price-block__final-price", 
                    ".price-block__final-price ins",
                    "span.price-block__final-price",
                    ".final-price",
                    "[data-link='text{:product^price}']"
                ]
                
                base_price = None
                for selector in base_price_selectors:
                    try:
                        base_price_element = driver.find_element("css selector", selector)
                        base_price_text = base_price_element.text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                        if base_price_text:
                            base_price = int(base_price_text)
                            logger.debug(f"📊 Основная цена найдена ({selector}): {base_price} ₽")
                            break
                    except:
                        continue
                
                # Вычисляем процент скидки по карте
                if price_with_card and base_price and base_price > 0:
                    card_discount_percent = round((1 - price_with_card / base_price) * 100, 1)
                    logger.debug(f"📉 Скидка по карте WB: {card_discount_percent}%")
                elif price_with_card:
                    logger.debug(f"⚠️ Не удалось найти основную цену для расчета скидки")
            except Exception as e:
                logger.debug(f"Ошибка поиска основной цены: {e}")
            
            # Собираем запросы
            logger.debug(f"Перехвачено запросов: {len(driver.requests)}")
            result = None
            for request in driver.requests:
                if "u-card.wb.ru/cards/v4/detail" in request.url and request.response:
                    params = parse_qs(urlparse(request.url).query)
                    params_simple = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
                    
                    body = request.response.body or b""
                    extracted = self._extract_prices_and_stocks(body, target_id=article_id)
                    
                    if extracted:
                        item = extracted[0]
                        
                        # Вычисляем SPP
                        price_basic = item.get("price_basic", 0)
                        price_product = item.get("price_product", 0)
                        spp_real = round(
                            100 - (price_product / price_basic * 100), 2
                        ) if price_basic else 0
                        
                        dest = params_simple.get("dest", "123585633")
                        
                        result = ParsingResult(
                            article_id=article_id,
                            account_uuid=account_uuid,
                            spp=spp_real,
                            dest=dest,
                            price_basic=price_basic,
                            price_product=price_product,
                            price_with_card=price_with_card,
                            card_discount_percent=card_discount_percent,
                            qty=item.get("qty", 0)
                        )
                        
                        card_info = ""
                        if price_with_card:
                            card_info = f" | 💳 {price_with_card}₽"
                            if card_discount_percent:
                                card_info += f" (-{card_discount_percent}%)"
                        
                        logger.success(
                            f"✅ {item.get('brand')} | "
                            f"{price_product/100:.2f}₽ из {price_basic/100:.2f}₽ "
                            f"(SPP {spp_real}%) | dest={dest} | qty={item.get('qty')}{card_info}"
                        )
                        break
            
            if not result:
                logger.warning(f"⚠️ Не найдены данные для артикула {article_id} (запросов: {len(driver.requests)})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {article_id}: {e}")
            return None
        finally:
            driver.quit()
    
    def parse_all_articles(self) -> int:
        """
        Парсинг всех артикулов через все аккаунты.
        
        Returns:
            int: Количество успешных парсингов
        """
        logger.info("🚀 Запуск парсинга всех артикулов...")
        
        articles = article_storage.get_all_articles()
        accounts = account_storage.get_all_accounts()
        
        if not articles:
            logger.warning("⚠️ Нет артикулов для парсинга")
            return 0
        
        if not accounts:
            logger.warning("⚠️ Нет аккаунтов для парсинга")
            return 0
        
        total_parsed = 0
        
        for article in articles:
            logger.info(f"📦 Парсинг артикула {article.article_id}...")
            
            for account in accounts:
                if not account.cookies:
                    logger.warning(f"⚠️ У аккаунта {account.name} нет cookies")
                    continue
                
                result = self.parse_article(
                    article.article_id,
                    str(account.uuid),
                    account.cookies
                )
                
                if result:
                    article_storage.add_parsing_result(result)
                    total_parsed += 1
                
                time.sleep(2)  # Пауза между запросами
            
            # Обновляем аналитику для артикула
            article_storage.update_analytics(article.article_id)
        
        logger.success(f"✅ Парсинг завершен. Обработано: {total_parsed} записей")
        return total_parsed


# Глобальный экземпляр сервиса
wb_parser = WBParserService(headless=settings.PARSING_HEADLESS)

