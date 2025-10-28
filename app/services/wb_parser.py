"""
Сервис парсинга Wildberries

Парсинг SPP и аналитика по артикулам.
"""

import time
import json
import concurrent.futures
from typing import Optional, List, Dict
from uuid import uuid4

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from app.core import logger, settings
from app.db import account_storage, article_storage
from app.models import ParsingResult


class WBParserService:
    """Сервис для парсинга данных с Wildberries"""
    
    def __init__(self, headless: bool = True):
        """Инициализация сервиса"""
        self.headless = headless
    
    
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
                # Дополнительные настройки для прокси
                options.add_argument('--proxy-bypass-list=<-loopback>')
                options.add_argument('--disable-web-security')
                options.add_argument('--disable-features=VizDisplayCompositor')
                options.add_argument('--ignore-certificate-errors')
                options.add_argument('--ignore-ssl-errors')
                options.add_argument('--ignore-certificate-errors-spki-list')
                logger.info(f"🌐 Используем прокси для парсинга: {proxy_host}:{proxy_port}")
                
                # Проверяем доступность прокси
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((proxy_host, int(proxy_port)))
                    sock.close()
                    if result != 0:
                        logger.warning(f"⚠️ Прокси {proxy_host}:{proxy_port} недоступен")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка проверки прокси: {e}")
            else:
                logger.warning("⚠️ Неполные данные прокси, парсим без прокси")
        
        # Используем ПРАВИЛЬНЫЙ chromedriver
        from selenium.webdriver.chrome.service import Service
        
        chromedriver_path = '/usr/bin/chromedriver'
        logger.info(f"🚀 Запуск парсера через ChromeDriver: {chromedriver_path}")
        
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
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
                    ".productPrice--FrVYO",  # Основной блок цены
                    ".priceBlock--ZADKT",  # Блок цены
                    ".priceDetailsPointer--pPAL4",  # Указатель детализации
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
                else:
                    logger.debug("✅ Попап открыт, парсим цены из него...")
                    
                    # Ищем цены в попапе
                    popup_price_selectors = [
                        ".walletPriceWrap--GjYV7 h2",  # Цена с картой в попапе
                        ".finalPriceWrap--tKHRP h2",   # SPP цена в попапе
                        ".finalPriceWrap--tKHRP span", # Старая цена в попапе
                        "h2",  # Заголовки с ценами
                        ".price-details-price",
                        "[class*='price']"
                    ]
                    
                    for selector in popup_price_selectors:
                        try:
                            elements = driver.find_elements("css selector", selector)
                            for element in elements:
                                text = element.text.strip()
                                if "₽" in text and any(char.isdigit() for char in text):
                                    price_text = text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                                    if price_text.isdigit():
                                        if not price_with_card:
                                            price_with_card = int(price_text)
                                            logger.debug(f"💳 Цена с картой найдена: {price_with_card} ₽")
                                        elif not base_price:
                                            base_price = int(price_text)
                                            logger.debug(f"📊 Обычная цена найдена: {base_price} ₽")
                                            break
                            if base_price:
                                break
                        except:
                            continue
                
                # 2. Парсим цены из попапа или с основной страницы
                time.sleep(1)  # Дополнительная пауза для загрузки
                
                # Проверяем на ошибки Chrome
                page_title = driver.title.lower()
                page_source = driver.page_source.lower()
                
                if "this site can't be reached" in page_source or "err_no_supported_proxies" in page_source:
                    logger.error(f"🚫 Ошибка прокси для {article_id}: ERR_NO_SUPPORTED_PROXIES")
                    logger.error(f"🌐 Прокси не поддерживается или заблокирован Wildberries")
                    return ParsingResult(
                        article_id=article_id,
                        account_uuid=account_uuid,
                        spp=0,
                        dest="123585633",
                        price_basic=0,
                        price_product=0,
                        price_with_card=0,
                        card_discount_percent=0,
                        qty=0
                    )
                
                if "site can't be reached" in page_source or "temporarily down" in page_source:
                    logger.error(f"🚫 Сайт недоступен для {article_id}")
                    return ParsingResult(
                        article_id=article_id,
                        account_uuid=account_uuid,
                        spp=0,
                        dest="123585633",
                        price_basic=0,
                        price_product=0,
                        price_with_card=0,
                        card_discount_percent=0,
                        qty=0
                    )
                
                # Сохраняем HTML для анализа если ничего не найдено
                if not price_with_card and not base_price:
                    try:
                        html_content = driver.page_source
                        with open(f"wb_page_debug_{article_id}.html", "w", encoding="utf-8") as f:
                            f.write(html_content)
                        logger.debug(f"💾 HTML страницы сохранен: wb_page_debug_{article_id}.html")
                    except Exception as e:
                        logger.debug(f"❌ Ошибка сохранения HTML: {e}")
                
                # УНИВЕРСАЛЬНЫЕ СЕЛЕКТОРЫ для поиска любых цен
                universal_price_selectors = [
                    # Все элементы с ценами
                    "[class*='price']",
                    "[class*='Price']", 
                    "span:contains('₽')",
                    "div:contains('₽')",
                    "ins:contains('₽')",
                    "h2:contains('₽')",
                    "h3:contains('₽')",
                    # По тексту содержащему ₽
                    "*:contains('₽')",
                    # Все span и div с числами
                    "span",
                    "div",
                    "ins",
                    "h1", "h2", "h3", "h4", "h5", "h6"
                ]
                
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
                    
                    # УНИВЕРСАЛЬНЫЙ ПОИСК всех элементов с ценами
                    logger.debug("🔍 Универсальный поиск всех цен...")
                    try:
                        # Используем XPath для более точного поиска
                        all_elements = driver.find_elements("xpath", "//*[contains(text(), '₽')]")
                        prices_found = []
                        
                        logger.debug(f"🔍 Найдено {len(all_elements)} элементов с ₽")
                        
                        for element in all_elements:
                            try:
                                text = element.text.strip()
                                if text and len(text) < 100:  # Ограничиваем длину текста
                                    # Улучшенное извлечение цены
                                    import re
                                    # Ищем числа в тексте (включая пробелы и неразрывные пробелы)
                                    numbers = re.findall(r'[\d\s\xa0\u00A0]+', text)
                                    for num in numbers:
                                        clean_num = num.replace(" ", "").replace("\xa0", "").replace("\u00A0", "").replace("&nbsp;", "").strip()
                                        if clean_num.isdigit() and len(clean_num) >= 2:  # Минимум 2 цифры
                                            price_value = int(clean_num)
                                            if 10 <= price_value <= 1000000:  # Разумные пределы цен
                                                prices_found.append({
                                                    'price': price_value,
                                                    'text': text,
                                                    'tag': element.tag_name,
                                                    'class': element.get_attribute('class') or '',
                                                    'id': element.get_attribute('id') or ''
                                                })
                                                logger.debug(f"💰 Найдена цена: {price_value}₽ | '{text}' | {element.tag_name} | {element.get_attribute('class')[:30]}")
                                                break
                            except Exception as e:
                                continue
                        
                        # Убираем дубликаты по цене
                        unique_prices = {}
                        for p in prices_found:
                            if p['price'] not in unique_prices:
                                unique_prices[p['price']] = p
                        
                        prices_found = list(unique_prices.values())
                        # Сортируем цены по убыванию
                        prices_found.sort(key=lambda x: x['price'], reverse=True)
                        
                        if prices_found:
                            logger.debug(f"📊 Найдено {len(prices_found)} уникальных цен:")
                            for i, price_info in enumerate(prices_found[:10]):  # Показываем первые 10
                                logger.debug(f"  {i+1}. {price_info['price']}₽ | '{price_info['text']}' | {price_info['tag']} | {price_info['class'][:30]}")
                            
                            # УМНАЯ ЛОГИКА ВЫБОРА ЦЕН
                            if len(prices_found) >= 3:
                                # Если есть 3+ цены, берем по логике:
                                # 1. Самая большая = старая цена (базовая цена продавца)
                                # 2. Вторая = SPP цена (цена с скидкой продавца)
                                # 3. Третья = цена с картой WB
                                old_price = prices_found[0]['price']
                                base_price = prices_found[1]['price'] 
                                price_with_card = prices_found[2]['price']
                                logger.debug(f"🎯 3+ цен: старая={old_price}₽, SPP={base_price}₽, карта={price_with_card}₽")
                            elif len(prices_found) == 2:
                                # Если 2 цены, берем большую как SPP, меньшую как карту
                                base_price = prices_found[0]['price']
                                price_with_card = prices_found[1]['price']
                                logger.debug(f"🎯 2 цены: SPP={base_price}₽, карта={price_with_card}₽")
                            elif len(prices_found) == 1:
                                # Если 1 цена, берем как SPP
                                base_price = prices_found[0]['price']
                                logger.debug(f"🎯 1 цена: SPP={base_price}₽")
                        else:
                            logger.debug("❌ Цены не найдены универсальным поиском")
                                
                    except Exception as e:
                        logger.debug(f"❌ Ошибка универсального поиска: {e}")
                    
                    # Старые селекторы для цены с картой
                    old_card_selectors = [
                        "span.priceBlockWalletPrice--RJGuT.redPrice--iueN6",
                        "span.priceBlockWalletPrice--RJGuT",
                        ".redPrice--iueN6",
                        "span[class*='redPrice']",
                        "[class*='wallet'][class*='price']",
                        "span[class*='wallet']"
                    ]
                    
                    for selector in old_card_selectors:
                        try:
                            logger.debug(f"🔍 Пробуем селектор карты: {selector}")
                            element = driver.find_element("css selector", selector)
                            text = element.text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                            logger.debug(f"📝 Текст элемента: '{element.text}' -> '{text}'")
                            if text.isdigit():
                                price_with_card = int(text)
                                logger.debug(f"💳 Цена с картой найдена: {price_with_card} ₽")
                                break
                        except Exception as e:
                            logger.debug(f"❌ Селектор {selector} не найден: {e}")
                            continue
                    
                    # Старые селекторы для основной цены (SPP цена)
                    old_base_selectors = [
                        "ins.priceBlockFinalPrice--iToZR.wallet--N1t3o",
                        "ins.priceBlockFinalPrice--iToZR",
                        ".priceBlockFinalPrice--iToZR",
                        "ins[class*='priceBlockFinalPrice']",
                        "ins.price-block__final-price",
                        ".price-block__final-price",
                        "span.price-block__final-price"
                    ]
                    
                    # Селекторы для старой цены (базовая цена продавца)
                    old_price_selectors = [
                        "span.priceBlockOldPrice--qSWAf",
                        ".priceBlockOldPrice--qSWAf",
                        "span[class*='OldPrice']",
                        "span[class*='old']",
                        "del",
                        "s",
                        "span[style*='line-through']"
                    ]
                    
                    for selector in old_base_selectors:
                        try:
                            logger.debug(f"🔍 Пробуем селектор основной цены: {selector}")
                            element = driver.find_element("css selector", selector)
                            text = element.text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                            logger.debug(f"📝 Текст элемента: '{element.text}' -> '{text}'")
                            if text.isdigit():
                                base_price = int(text)
                                logger.debug(f"💰 Основная цена найдена: {base_price} ₽")
                                break
                        except Exception as e:
                            logger.debug(f"❌ Селектор {selector} не найден: {e}")
                            continue
                    
                    # Поиск старой цены (базовая цена продавца)
                    for selector in old_price_selectors:
                        try:
                            logger.debug(f"🔍 Пробуем селектор старой цены: {selector}")
                            element = driver.find_element("css selector", selector)
                            text = element.text.replace("₽", "").replace(" ", "").replace("\xa0", "").strip()
                            logger.debug(f"📝 Текст старой цены: '{element.text}' -> '{text}'")
                            if text.isdigit():
                                old_price = int(text)
                                logger.debug(f"💰 Старая цена найдена: {old_price} ₽")
                                break
                        except Exception as e:
                            logger.debug(f"❌ Селектор {selector} не найден: {e}")
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
            
            # Простой парсинг HTML (без перехвата запросов)
            logger.debug("🔍 Парсинг данных с HTML страницы...")
            
            # Пытаемся найти данные на странице
            result = None
            try:
                # Ищем название товара
                brand = "Unknown"
                try:
                    brand_element = driver.find_element("css selector", "h1[data-link='text{:product^goodsName}']")
                    brand = brand_element.text.strip()
                except:
                    pass
                
                # Ищем количество
                qty = 0
                try:
                    qty_element = driver.find_element("css selector", "[data-link='text{:product^totalQuantity}']")
                    qty_text = qty_element.text.replace("шт.", "").strip()
                    qty = int(qty_text) if qty_text.isdigit() else 0
                except:
                    pass
                
                # ПРАВИЛЬНАЯ ЛОГИКА ЦЕН:
                # 1. price_base - старая цена (базовая цена продавца)
                # 2. price_spp - цена с SPP (текущая цена с скидкой продавца) 
                # 3. price_card - цена с картой WB (доп. скидка от SPP)
                
                price_base = old_price or 0        # Старая цена (зачеркнутая)
                price_spp = base_price or 0        # Текущая цена (SPP)
                price_card = price_with_card or 0  # Цена с картой WB
                
                # Вычисляем SPP (скидка продавца от базовой цены)
                spp_real = 0
                if price_base and price_spp and price_base > price_spp:
                    spp_real = round((1 - price_spp / price_base) * 100, 2)
                
                # Вычисляем скидку карты (дополнительная скидка от SPP цены)
                card_discount_real = 0
                if price_spp and price_card and price_spp > price_card:
                    card_discount_real = round((1 - price_card / price_spp) * 100, 2)
                
                # Создаем результат
                result = ParsingResult(
                    article_id=article_id,
                    account_uuid=account_uuid,
                    spp=spp_real,
                    dest="123585633",  # Дефолтный dest
                    price_basic=price_base,      # Базовая цена продавца
                    price_product=price_spp,     # Цена с SPP
                    price_with_card=price_card,  # Цена с картой WB
                    card_discount_percent=card_discount_real,  # Скидка карты от SPP
                    qty=qty
                )
                
                card_info = ""
                if price_card:
                    card_info = f" | 💳 {price_card}₽"
                    if card_discount_real:
                        card_info += f" (-{card_discount_real}%)"
                    if old_price:
                        card_info += f" | 📉 Было: {old_price}₽"
                
                logger.success(
                    f"✅ {brand} | "
                    f"{price_spp/100:.2f}₽ из {price_base/100:.2f}₽ "
                    f"(SPP {spp_real}%) | qty={qty}{card_info}"
                )
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка парсинга HTML: {e}")
            
            if not result:
                logger.warning(f"⚠️ Не найдены данные для артикула {article_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {article_id}: {e}")
            return None
        finally:
            driver.quit()
    
    def parse_all_articles(self) -> int:
        """
        Парсинг всех артикулов с приоритизацией по прокси.
        
        Логика:
        1. Аккаунты С прокси - парсятся ПАРАЛЛЕЛЬНО (до 5 потоков)
        2. Аккаунты БЕЗ прокси - парсятся ПОСЛЕДОВАТЕЛЬНО
        
        Returns:
            int: Количество успешных парсингов
        """
        logger.info("🚀 Запуск парсинга всех артикулов с приоритизацией...")
        
        articles = article_storage.get_all_articles()
        accounts = account_storage.get_all_accounts()
        
        if not articles:
            logger.warning("⚠️ Нет артикулов для парсинга")
            return 0
        
        if not accounts:
            logger.warning("⚠️ Нет аккаунтов для парсинга")
            return 0
        
        # Разделяем аккаунты на группы
        accounts_with_proxy = []
        accounts_without_proxy = []
        
        from app.db.proxy_storage import ProxyStorage
        proxy_storage = ProxyStorage()
        
        for account in accounts:
            if not account.cookies:
                logger.warning(f"⚠️ У аккаунта {account.name} нет cookies")
                continue
                
            # Проверяем есть ли прокси у аккаунта
            proxy_uuid = getattr(account, 'proxy_uuid', None)
            if proxy_uuid:
                proxy_data = proxy_storage.get_proxy(proxy_uuid)
                if proxy_data:
                    accounts_with_proxy.append((account, proxy_data))
                    logger.debug(f"🌐 Аккаунт {account.name} с прокси {proxy_data['name']}")
                else:
                    accounts_without_proxy.append((account, None))
                    logger.warning(f"⚠️ У аккаунта {account.name} прокси не найден")
            else:
                accounts_without_proxy.append((account, None))
                logger.debug(f"📱 Аккаунт {account.name} без прокси")
        
        logger.info(f"📊 Статистика: {len(accounts_with_proxy)} с прокси, {len(accounts_without_proxy)} без прокси")
        
        total_parsed = 0
        
        # 1. ПАРСИМ АККАУНТЫ С ПРОКСИ (параллельно, до 5 потоков)
        if accounts_with_proxy:
            logger.info("🌐 Парсинг аккаунтов с прокси (параллельно)...")
            total_parsed += self._parse_with_proxy_parallel(articles, accounts_with_proxy)
        
        # 2. ПАРСИМ АККАУНТЫ БЕЗ ПРОКСИ (последовательно)
        if accounts_without_proxy:
            logger.info("📱 Парсинг аккаунтов без прокси (последовательно)...")
            total_parsed += self._parse_without_proxy_sequential(articles, accounts_without_proxy)
        
        # 3. ОБНОВЛЯЕМ АНАЛИТИКУ ДЛЯ ВСЕХ АРТИКУЛОВ
        for article in articles:
            article_storage.update_analytics(article.article_id)
        
        logger.success(f"✅ Парсинг завершен. Обработано: {total_parsed} записей")
        return total_parsed
    
    def _parse_with_proxy_parallel(self, articles, accounts_with_proxy) -> int:
        """
        Параллельный парсинг аккаунтов с прокси (до 5 потоков).
        
        Args:
            articles: Список артикулов
            accounts_with_proxy: Список (аккаунт, прокси_данные)
            
        Returns:
            int: Количество успешных парсингов
        """
        import threading
        
        total_parsed = 0
        max_workers = min(5, len(accounts_with_proxy))  # До 5 потоков
        
        logger.info(f"🌐 Запуск параллельного парсинга: {max_workers} потоков")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Создаем задачи для каждого артикула
            futures = []
            
            for article in articles:
                logger.info(f"📦 Парсинг артикула {article.article_id} (параллельно)...")
                
                # Создаем задачи для всех аккаунтов с прокси
                for account, proxy_data in accounts_with_proxy:
                    future = executor.submit(
                        self._parse_single_article_with_proxy,
                        article.article_id,
                        str(account.uuid),
                        account.cookies,
                        proxy_data
                    )
                    futures.append(future)
            
            # Ждем завершения всех задач
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        article_storage.add_parsing_result(result)
                        total_parsed += 1
                        logger.debug(f"✅ Результат сохранен для артикула {result.article_id}")
                except Exception as e:
                    logger.error(f"❌ Ошибка в параллельном парсинге: {e}")
        
        logger.info(f"🌐 Параллельный парсинг завершен: {total_parsed} записей")
        return total_parsed
    
    def _parse_without_proxy_sequential(self, articles, accounts_without_proxy) -> int:
        """
        Последовательный парсинг аккаунтов без прокси.
        
        Args:
            articles: Список артикулов
            accounts_without_proxy: Список (аккаунт, None)
            
        Returns:
            int: Количество успешных парсингов
        """
        total_parsed = 0
        
        logger.info(f"📱 Запуск последовательного парсинга: {len(accounts_without_proxy)} аккаунтов")
        
        for article in articles:
            logger.info(f"📦 Парсинг артикула {article.article_id} (последовательно)...")
            
            for account, _ in accounts_without_proxy:
                logger.debug(f"📱 Парсинг через аккаунт {account.name} (без прокси)")
                
                result = self.parse_article(
                    article.article_id,
                    str(account.uuid),
                    account.cookies,
                    proxy_data=None  # Без прокси
                )
                
                if result:
                    article_storage.add_parsing_result(result)
                    total_parsed += 1
                
                time.sleep(2)  # Пауза между запросами без прокси
        
        logger.info(f"📱 Последовательный парсинг завершен: {total_parsed} записей")
        return total_parsed
    
    def _parse_single_article_with_proxy(self, article_id, account_uuid, cookies, proxy_data):
        """
        Парсинг одного артикула с прокси (для параллельного выполнения).
        
        Args:
            article_id: ID артикула
            account_uuid: UUID аккаунта
            cookies: Cookies аккаунта
            proxy_data: Данные прокси
            
        Returns:
            ParsingResult или None
        """
        try:
            logger.debug(f"🌐 Парсинг {article_id} через {account_uuid} с прокси {proxy_data['name']}")
            
            result = self.parse_article(
                article_id,
                account_uuid,
                cookies,
                proxy_data=proxy_data
            )
            
            if result:
                logger.debug(f"✅ Успешно спарсен {article_id} через {account_uuid}")
            else:
                logger.warning(f"⚠️ Не удалось спарсить {article_id} через {account_uuid}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {article_id} через {account_uuid}: {e}")
            return None


# Глобальный экземпляр сервиса
wb_parser = WBParserService(headless=settings.PARSING_HEADLESS)

