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
    
    def _start_browser(self) -> webdriver.Chrome:
        """
        Запуск браузера Chrome.
        
        Returns:
            webdriver.Chrome: Экземпляр драйвера
        """
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        
        # Флаги для работы без GPU (Ubuntu сервер)
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-setuid-sandbox")
        
        # Остальные флаги
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1280,2400")
        opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        
        # Отключаем использование профиля - Chrome сам создаст временный
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-default-apps")
        
        # Дополнительные флаги для стабильности
        opts.add_argument("--single-process")
        opts.add_argument("--disable-features=VizDisplayCompositor")
        
        logger.debug("Запуск Chrome с headless режимом")
        
        try:
            import undetected_chromedriver as uc
            
            logger.info("🚀 Запускаем Chrome через undetected-chromedriver")
            
            # Создаем опции для undetected_chromedriver
            uc_options = uc.ChromeOptions()
            
            # Копируем все опции из opts (кроме headless - он конфликтует)
            for arg in opts.arguments:
                if '--headless' not in arg:
                    uc_options.add_argument(arg)
            
            # Для headless на сервере используем новый режим
            if self.headless:
                uc_options.add_argument('--headless=new')
            
            # undetected_chromedriver автоматически найдет Chrome и скачает подходящий драйвер
            driver = uc.Chrome(
                options=uc_options,
                headless=False,  # НЕ используем встроенный headless uc
                use_subprocess=False,  # Важно для стабильности
                version_main=None  # Автоопределение версии
            )
            
            logger.info("✅ Chrome успешно запущен через undetected-chromedriver")
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
        auth_session
    ) -> Optional[str]:
        """
        Авторизация в WB и получение cookies через WebSocket.
        
        Args:
            phone: Номер телефона без +7
            auth_session: Сессия авторизации с WebSocket
            
        Returns:
            Optional[str]: JSON строка с cookies или None при ошибке
        """
        driver = self._start_browser()
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

