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
        cookies: str,
        proxy_data: Optional[dict] = None
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
        
        # ВАЖНО: указываем путь к Chrome бинарнику
        options.binary_location = "/opt/chrome/chrome"
        
        # Флаги для headless режима
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        
        # Настройка прокси если передан
        if proxy_data:
            proxy_host = proxy_data.get('host')
            proxy_port = proxy_data.get('port')
            proxy_username = proxy_data.get('username')
            proxy_password = proxy_data.get('password')
            
            if proxy_host and proxy_port:
                # Формируем строку прокси
                if proxy_username and proxy_password:
                    proxy_string = f"{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                else:
                    proxy_string = f"{proxy_host}:{proxy_port}"
                
                options.add_argument(f"--proxy-server=http://{proxy_string}")
                logger.info(f"🌐 Используем прокси для парсинга: {proxy_host}:{proxy_port}")
            else:
                logger.warning("⚠️ Неполные данные прокси, парсим без прокси")
        
        # Используем ПРАВИЛЬНЫЙ chromedriver
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
            
            # Собираем цены из попапа "Детализация цены"
            price_with_card = None
            card_discount_percent = None
            old_price = None
            base_price = None
            
            try:
                # 1. Пытаемся открыть попап "Детализация цены"
                logger.debug("🔍 Ищем кнопку для открытия попапа Детализация цены...")
                
                popup_selectors = [
                    "button[data-link='text{:product^price}']",  # Кнопка цены
                    ".price-block__final-price",  # Клик по цене
                    "ins.priceBlockFinalPrice--iToZR",  # Основная цена
                    ".price-block",  # Блок с ценой
                    "[data-link*='price']",  # Любой элемент с price в data-link
                    "button[aria-label*='цена']",  # Кнопка с aria-label
                    ".price-block__final-price ins"  # Инс с ценой
                ]
                
                popup_opened = False
                for selector in popup_selectors:
                    try:
                        element = driver.find_element("css selector", selector)
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(2)  # Ждем появления попапа
                        
                        # Проверяем, появился ли попап
                        popup_check = driver.find_elements("css selector", "[class*='popup'], [class*='modal'], [class*='details']")
                        if popup_check:
                            logger.debug(f"✅ Попап открыт через селектор: {selector}")
                            popup_opened = True
                            break
                    except:
                        continue
                
                if not popup_opened:
                    logger.debug("⚠️ Попап не открылся, пробуем парсить без него")
                
                # 2. Парсим цены из попапа или с основной страницы
                time.sleep(1)  # Дополнительная пауза для загрузки
                
                # Ищем цену "с WB Кошельком" (розовая)
                wb_wallet_selectors = [
                    "[class*='wallet'][class*='price']",  # Элементы с wallet и price
                    "[class*='WB'][class*='price']",  # Элементы с WB и price
                    "span[class*='wallet']",  # Span с wallet
                    ".price-details [class*='wallet']",  # В блоке price-details
                    "[data-testid*='wallet']",  # По data-testid
                    "div[class*='pink'], div[class*='red']"  # Розовые/красные блоки
                ]
                
                for selector in wb_wallet_selectors:
                    try:
                        elements = driver.find_elements("css selector", selector)
                        for element in elements:
                            text = element.text.strip()
                            if "₽" in text and any(char.isdigit() for char in text):
                                price_text = text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                                if price_text.isdigit():
                                    price_with_card = int(price_text)
                                    logger.debug(f"💳 Цена с WB Кошельком найдена: {price_with_card} ₽")
                                    break
                        if price_with_card:
                            break
                    except:
                        continue
                
                # Ищем цену "без WB Кошелька" (серая)
                regular_price_selectors = [
                    "[class*='regular'][class*='price']",  # Обычная цена
                    "[class*='without'][class*='wallet']",  # Без кошелька
                    ".price-details [class*='without']",  # В блоке price-details
                    "div[class*='gray'], div[class*='white']"  # Серые/белые блоки
                ]
                
                for selector in regular_price_selectors:
                    try:
                        elements = driver.find_elements("css selector", selector)
                        for element in elements:
                            text = element.text.strip()
                            if "₽" in text and any(char.isdigit() for char in text):
                                price_text = text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                                if price_text.isdigit():
                                    base_price = int(price_text)
                                    logger.debug(f"📊 Обычная цена найдена: {base_price} ₽")
                                    break
                        if base_price:
                            break
                    except:
                        continue
                
                # Если не нашли в попапе, пробуем старые селекторы
                if not price_with_card or not base_price:
                    logger.debug("🔄 Пробуем старые селекторы...")
                    
                    # Старые селекторы для цены с картой
                    old_card_selectors = [
                        "span.priceBlockWalletPrice--RJGuT",
                        "[class*='wallet'][class*='price']",
                        "span[class*='wallet']"
                    ]
                    
                    for selector in old_card_selectors:
                        try:
                            element = driver.find_element("css selector", selector)
                            text = element.text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                            if text.isdigit():
                                price_with_card = int(text)
                                logger.debug(f"💳 Цена с картой (старый селектор): {price_with_card} ₽")
                                break
                        except:
                            continue
                    
                    # Старые селекторы для основной цены
                    old_base_selectors = [
                        "ins.priceBlockFinalPrice--iToZR",
                        "ins.price-block__final-price",
                        ".price-block__final-price",
                        "span.price-block__final-price"
                    ]
                    
                    for selector in old_base_selectors:
                        try:
                            element = driver.find_element("css selector", selector)
                            text = element.text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                            if text.isdigit():
                                base_price = int(text)
                                logger.debug(f"📊 Основная цена (старый селектор): {base_price} ₽")
                                break
                        except:
                            continue
                
                # Вычисляем скидку по карте
                if base_price and price_with_card and base_price > price_with_card:
                    card_discount_percent = round(
                        ((base_price - price_with_card) / base_price * 100), 2
                    )
                    logger.debug(f"💳 Скидка по карте WB: {card_discount_percent}%")
                
                # Ищем старую цену (зачеркнутую)
                old_price_selectors = [
                    "span.priceBlockOldPrice--qSWAf",
                    "span[class*='old']",
                    "del",
                    "s",
                    "[class*='old'][class*='price']"
                ]
                
                for selector in old_price_selectors:
                    try:
                        element = driver.find_element("css selector", selector)
                        text = element.text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                        if text.isdigit():
                            old_price = int(text)
                            logger.debug(f"📉 Старая цена: {old_price} ₽")
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"Ошибка при парсинге цен: {e}")
            
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
                            if old_price:
                                card_info += f" | 📉 Было: {old_price}₽"
                        
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

