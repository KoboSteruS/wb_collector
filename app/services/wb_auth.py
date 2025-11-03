"""
Сервис авторизации в Wildberries

Автоматизация входа в аккаунт WB через Selenium.
"""

import time
import json
import tempfile
from typing import Optional
from uuid import uuid4

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app.core import logger


class WBAuthService:
    """
    Сервис для авторизации в Wildberries.
    
    Использует Selenium для автоматизации процесса входа.
    """
    
    def __init__(self, headless: bool = True):
        """
        Инициализация сервиса.
        
        Args:
            headless: Запуск браузера в фоновом режиме
        """
        self.headless = headless
    
    def _start_browser(self, proxy_data: Optional[dict] = None) -> webdriver.Chrome:
        """
        Запуск браузера Chrome с поддержкой прокси.
        
        Args:
            proxy_data: Данные прокси (host, port, username, password)
        
        Returns:
            webdriver.Chrome: Экземпляр драйвера
        """
        from selenium.webdriver.chrome.service import Service
        
        opts = Options()
        
        # Для Windows - не указываем binary_location (используем системный Chrome)
        import platform
        if platform.system() != "Windows":
            # Только для Linux сервера
            opts.binary_location = "/opt/chrome/chrome"
        
        # Флаги для headless режима
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1920,1080")
        
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
                
                opts.add_argument(f"--proxy-server=http://{proxy_string}")
                logger.info(f"🌐 Используем прокси: {proxy_host}:{proxy_port}")
            else:
                logger.warning("⚠️ Неполные данные прокси, запускаем без прокси")
        
        logger.debug("Запуск Chrome в headless режиме")
        
        try:
            logger.info("🚀 Запускаем Chrome через Selenium")
            
            # Используем webdriver-manager для автоматической установки ChromeDriver
            import platform
            if platform.system() == "Windows":
                # Для Windows - автоматическая установка ChromeDriver
                service = Service(ChromeDriverManager().install())
            else:
                # Для Linux сервера - используем системный chromedriver
                service = Service(executable_path='/usr/bin/chromedriver')
            
            driver = webdriver.Chrome(service=service, options=opts)
            
            logger.info("✅ Chrome успешно запущен!")
            return driver
        except Exception as e:
            logger.error(f"❌ Ошибка запуска Chrome: {e}")
            raise
    
    def _safe_click(self, driver: webdriver.Chrome, elem) -> bool:
        """
        Безопасный клик по элементу с обходом перекрытий.
        
        Args:
            driver: Драйвер браузера
            elem: Элемент для клика
            
        Returns:
            bool: Успешность клика
        """
        try:
            elem.click()
            return True
        except Exception:
            try:
                ActionChains(driver).move_to_element(elem).click().perform()
                return True
            except Exception:
                return False
    
    async def login_and_get_cookies_with_ws(
        self,
        phone: str,
        auth_session,
        proxy_data: Optional[dict] = None
    ) -> Optional[str]:
        """
        Авторизация в WB и получение cookies через WebSocket.
        
        Args:
            phone: Номер телефона без +7
            auth_session: Сессия авторизации с WebSocket
            proxy_data: Данные прокси (опционально)
            
        Returns:
            Optional[str]: JSON строка с cookies или None при ошибке
        """
        driver = self._start_browser(proxy_data)
        wait = WebDriverWait(driver, 20)
        
        try:
            logger.info(f"Начало авторизации для номера {phone}")
            await auth_session.send_message("status", {
                "step": "started",
                "message": "Запуск браузера..."
            })
            
            driver.get("https://www.wildberries.ru/security/login")
            
            # Принятие cookies баннера
            try:
                cookie_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".cookies__btn"))
                )
                cookie_btn.click()
                logger.info("Баннер cookies принят")
            except:
                logger.warning("Баннер cookies не найден")
            
            await auth_session.send_message("status", {
                "step": "page_loaded",
                "message": "Страница авторизации загружена"
            })
            
            # Поиск поля ввода телефона
            logger.info("Поиск поля телефона...")
            phone_input = None
            for css in [
                "input[data-testid='phoneInput']",
                "input[inputmode='tel']",
                "input[type='tel']"
            ]:
                try:
                    phone_input = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, css))
                    )
                    if phone_input.is_displayed():
                        break
                except:
                    pass
            
            if not phone_input:
                raise Exception("Поле телефона не найдено")
            
            # ПЕРЕИСКИВАЕМ поле телефона перед использованием (может стать stale)
            logger.info("Переискиваем поле телефона перед вводом...")
            phone_input = None
            
            # Расширенный список селекторов (приоритетный селектор первым)
            selectors = [
                "input[data-testid*='phone']",  # Приоритетный селектор
                "input[placeholder*='000 000-00-00']",
                "input[placeholder*='000-00-00']", 
                "input[placeholder*='+7']",
                "input[type='tel']",
                "input[name*='phone']",
                "input[id*='phone']",
                "input[class*='phone']",
                "input[aria-label*='телефон']",
                "input[aria-label*='phone']"
            ]
            
            for css in selectors:
                try:
                    logger.debug(f"Пробуем селектор: {css}")
                    phone_input = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, css))
                    )
                    if phone_input.is_displayed():
                        logger.info(f"✅ Поле телефона найдено с селектором: {css}")
                        break
                except Exception as e:
                    logger.debug(f"❌ Селектор {css} не найден: {e}")
                    pass
            
            if not phone_input:
                # Сохраняем HTML для анализа
                html_content = driver.page_source
                with open("wb_page_source.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.error("HTML страницы сохранен в wb_page_source.html для анализа")
                raise Exception("Поле телефона не найдено при повторном поиске")
            
            # Ввод номера
            self._safe_click(driver, phone_input)
            phone_input.clear()
            logger.info(f"Ввод номера: {phone}")
            
            await auth_session.send_message("status", {
                "step": "entering_phone",
                "message": f"Ввод номера телефона {phone}"
            })
            
            for ch in phone:
                phone_input.send_keys(ch)
                time.sleep(0.07)
            
            # Проверка корректности ввода
            val = phone_input.get_attribute("value") or ""
            digits_only = "".join([c for c in val if c.isdigit()])
            
            if not digits_only.endswith(phone):
                raise Exception(f"Номер введен некорректно (value='{val}')")
            
            logger.info("Номер успешно введен")
            
            # Нажатие кнопки "Получить код"
            logger.info("Поиск кнопки 'Получить код'...")
            btn = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#requestCode, [data-testid='requestCodeBtn']"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.4)
            self._safe_click(driver, btn)
            logger.info("Клик по кнопке 'Получить код' выполнен")
            
            await auth_session.send_message("status", {
                "step": "code_requested",
                "message": "Запрос кода отправлен"
            })
            
            # Ожидание полей для кода
            logger.info("Ожидание полей для кода...")
            inputs = []
            for _ in range(30):
                inputs = driver.find_elements(By.CSS_SELECTOR, "input.j-b-charinput")
                if len(inputs) >= 4:
                    break
                time.sleep(1)
            
            if not inputs:
                raise Exception("Не найдены поля для ввода кода")
            
            logger.info(f"Найдено {len(inputs)} полей для кода")
            
            await auth_session.send_message("status", {
                "step": "waiting_for_code",
                "message": "Ожидание ввода кода подтверждения"
            })
            
            # Ожидание кода от пользователя через WebSocket
            logger.info("Ожидание кода от пользователя...")
            code = await auth_session.wait_for_code(timeout=300)
            
            if not code:
                raise Exception("Таймаут ожидания кода")
            
            logger.info("Код получен, вводим в поля...")
            await auth_session.send_message("status", {
                "step": "entering_code",
                "message": "Ввод кода подтверждения"
            })
            
            # ПЕРЕИСКИВАЕМ элементы после получения кода (могут измениться)
            logger.info("Переискиваем поля для кода...")
            inputs = []
            for _ in range(10):
                inputs = driver.find_elements(By.CSS_SELECTOR, "input.j-b-charinput")
                if len(inputs) >= 4:
                    break
                time.sleep(0.5)
            
            if not inputs:
                raise Exception("Не найдены поля для ввода кода после получения кода")
            
            logger.info(f"Найдено {len(inputs)} полей для кода (повторный поиск)")
            
            # Ввод кода в поля
            for i, ch in enumerate(code):
                if i < len(inputs):
                    inputs[i].send_keys(ch)
                    time.sleep(0.15)
            
            logger.info("Код введен, ожидание авторизации...")
            await auth_session.send_message("status", {
                "step": "verifying",
                "message": "Проверка кода..."
            })
            
            # Ожидание завершения авторизации
            time.sleep(5)
            
            # Получение cookies после авторизации
            cookies = driver.get_cookies()
            cookies_json = json.dumps(cookies, ensure_ascii=False)
            
            logger.info("Cookies успешно получены")
            await auth_session.send_message("status", {
                "step": "success",
                "message": "Авторизация успешно завершена"
            })
            
            return cookies_json
            
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            await auth_session.send_message("error", {
                "message": str(e)
            })
            try:
                driver.save_screenshot("wb_login_error.png")
                logger.info("Скриншот сохранен: wb_login_error.png")
            except:
                pass
            return None
            
        finally:
            driver.quit()

