"""
Модуль для работы с прокси данными
"""
import json
import os
from typing import List, Optional, Dict, Any
from uuid import uuid4
from loguru import logger


class ProxyStorage:
    """Класс для работы с прокси данными"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.proxies_file = os.path.join(data_dir, "proxies.json")
        self._ensure_data_dir()
        self._ensure_proxies_file()
    
    def _ensure_data_dir(self) -> None:
        """Создает директорию для данных если не существует"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.debug(f"📁 Создана директория данных: {self.data_dir}")
    
    def _ensure_proxies_file(self) -> None:
        """Создает файл прокси если не существует"""
        if not os.path.exists(self.proxies_file):
            with open(self.proxies_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            logger.debug(f"📄 Создан файл прокси: {self.proxies_file}")
    
    def add_proxy(self, name: str, host: str, port: int, username: Optional[str] = None, password: Optional[str] = None) -> str:
        """
        Добавляет новый прокси
        
        Args:
            name: Название прокси
            host: Хост прокси
            port: Порт прокси
            username: Логин (опционально)
            password: Пароль (опционально)
            
        Returns:
            UUID добавленного прокси
        """
        try:
            # Загружаем существующие прокси
            with open(self.proxies_file, 'r', encoding='utf-8') as f:
                proxies = json.load(f)
            
            # Создаем новый прокси
            proxy_uuid = str(uuid4())
            proxy_data = {
                "uuid": proxy_uuid,
                "name": name,
                "host": host,
                "port": port,
                "username": username,
                "password": password,
                "status": "active",
                "created_at": None,  # Будет заполнено в API
                "updated_at": None
            }
            
            # Добавляем в словарь
            proxies[proxy_uuid] = proxy_data
            
            # Сохраняем
            with open(self.proxies_file, 'w', encoding='utf-8') as f:
                json.dump(proxies, f, ensure_ascii=False, indent=2)
            
            logger.success(f"🌐 Прокси '{name}' ({host}:{port}) добавлен с UUID: {proxy_uuid}")
            return proxy_uuid
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления прокси: {e}")
            raise
    
    def get_proxy(self, proxy_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Получает прокси по UUID
        
        Args:
            proxy_uuid: UUID прокси
            
        Returns:
            Данные прокси или None
        """
        try:
            with open(self.proxies_file, 'r', encoding='utf-8') as f:
                proxies = json.load(f)
            
            return proxies.get(proxy_uuid)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения прокси {proxy_uuid}: {e}")
            return None
    
    def get_all_proxies(self) -> List[Dict[str, Any]]:
        """
        Получает все прокси
        
        Returns:
            Список всех прокси
        """
        try:
            with open(self.proxies_file, 'r', encoding='utf-8') as f:
                proxies = json.load(f)
            
            return list(proxies.values())
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка прокси: {e}")
            return []
    
    def delete_proxy(self, proxy_uuid: str) -> bool:
        """
        Удаляет прокси
        
        Args:
            proxy_uuid: UUID прокси
            
        Returns:
            True если удален, False если не найден
        """
        try:
            with open(self.proxies_file, 'r', encoding='utf-8') as f:
                proxies = json.load(f)
            
            if proxy_uuid not in proxies:
                logger.warning(f"⚠️ Прокси {proxy_uuid} не найден")
                return False
            
            proxy_name = proxies[proxy_uuid].get('name', 'Unknown')
            del proxies[proxy_uuid]
            
            with open(self.proxies_file, 'w', encoding='utf-8') as f:
                json.dump(proxies, f, ensure_ascii=False, indent=2)
            
            logger.success(f"🗑️ Прокси '{proxy_name}' ({proxy_uuid}) удален")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления прокси {proxy_uuid}: {e}")
            return False
    
    def update_proxy_status(self, proxy_uuid: str, status: str) -> bool:
        """
        Обновляет статус прокси
        
        Args:
            proxy_uuid: UUID прокси
            status: Новый статус
            
        Returns:
            True если обновлен, False если не найден
        """
        try:
            with open(self.proxies_file, 'r', encoding='utf-8') as f:
                proxies = json.load(f)
            
            if proxy_uuid not in proxies:
                logger.warning(f"⚠️ Прокси {proxy_uuid} не найден")
                return False
            
            proxies[proxy_uuid]['status'] = status
            
            with open(self.proxies_file, 'w', encoding='utf-8') as f:
                json.dump(proxies, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"🔄 Статус прокси {proxy_uuid} обновлен на: {status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса прокси {proxy_uuid}: {e}")
            return False
    
    def get_available_proxies(self) -> List[Dict[str, Any]]:
        """
        Получает доступные прокси (статус active)
        
        Returns:
            Список доступных прокси
        """
        all_proxies = self.get_all_proxies()
        return [proxy for proxy in all_proxies if proxy.get('status') == 'active']
    
    def get_proxy_for_account(self, account_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Получает прокси для конкретного аккаунта (простая ротация)
        
        Args:
            account_uuid: UUID аккаунта
            
        Returns:
            Прокси для аккаунта или None
        """
        available_proxies = self.get_available_proxies()
        
        if not available_proxies:
            logger.warning("⚠️ Нет доступных прокси")
            return None
        
        # Простая ротация по хешу UUID аккаунта
        import hashlib
        hash_value = int(hashlib.md5(account_uuid.encode()).hexdigest(), 16)
        proxy_index = hash_value % len(available_proxies)
        
        selected_proxy = available_proxies[proxy_index]
        logger.debug(f"🎯 Выбран прокси для аккаунта {account_uuid[:8]}: {selected_proxy['name']}")
        
        return selected_proxy
