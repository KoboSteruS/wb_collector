"""
Простое хранилище для аккаунтов

Временное решение до подключения полноценной БД.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from uuid import UUID

from app.models import Account
from app.core import logger


class AccountStorage:
    """
    Хранилище аккаунтов в файле JSON.
    
    Простое файловое хранилище для начальной разработки.
    """
    
    def __init__(self, storage_file: str = "data/accounts.json"):
        """
        Инициализация хранилища.
        
        Args:
            storage_file: Путь к файлу хранилища
        """
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.storage_file.exists():
            self._save_data({})
    
    def _load_data(self) -> Dict:
        """
        Загрузка данных из файла.
        
        Returns:
            Dict: Данные из хранилища
        """
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return {}
    
    def _save_data(self, data: Dict) -> None:
        """
        Сохранение данных в файл с резервным копированием.
        
        Args:
            data: Данные для сохранения
        """
        try:
            # Создаем резервную копию перед записью
            if self.storage_file.exists():
                backup_file = self.storage_file.with_suffix('.json.backup')
                import shutil
                shutil.copy2(self.storage_file, backup_file)
                logger.debug(f"📦 Резервная копия создана: {backup_file}")
            
            # Сохраняем во временный файл, затем переименовываем (атомарная операция)
            temp_file = self.storage_file.with_suffix('.json.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Атомарное переименование
            import os
            temp_file.replace(self.storage_file)
            logger.debug(f"💾 Данные сохранены в {self.storage_file}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
            raise
    
    def add_account(self, account: Account) -> bool:
        """
        Добавление нового аккаунта.
        
        Args:
            account: Аккаунт для добавления
            
        Returns:
            bool: Успешность операции
        """
        try:
            data = self._load_data()
            account_uuid = str(account.uuid)
            
            if account_uuid in data:
                logger.warning(f"⚠️ Аккаунт {account_uuid} уже существует")
                return False
            
            data[account_uuid] = account.to_dict()
            self._save_data(data)
            logger.success(f"💾 Аккаунт '{account.name}' (📱 {account.phone}) сохранен в БД")
            logger.debug(f"UUID аккаунта: {account_uuid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления аккаунта: {e}")
            return False
    
    def get_account(self, account_uuid: str) -> Optional[Account]:
        """
        Получение аккаунта по UUID.
        
        Args:
            account_uuid: UUID аккаунта
            
        Returns:
            Optional[Account]: Аккаунт или None
        """
        try:
            data = self._load_data()
            account_data = data.get(account_uuid)
            
            if not account_data:
                return None
            
            return Account(
                name=account_data["name"],
                phone=account_data["phone"],
                cookies=account_data.get("cookies"),
                proxy_uuid=account_data.get("proxy_uuid"),
                uuid=UUID(account_data["uuid"]),
                created_at=datetime.fromisoformat(account_data["created_at"]) if account_data.get("created_at") else None,
                updated_at=datetime.fromisoformat(account_data["updated_at"]) if account_data.get("updated_at") else None
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения аккаунта: {e}")
            return None
    
    def update_cookies(self, account_uuid: str, cookies: str) -> bool:
        """
        Обновление cookies аккаунта с резервным копированием.
        
        Args:
            account_uuid: UUID аккаунта
            cookies: Новые cookies
            
        Returns:
            bool: Успешность операции
        """
        try:
            import json as json_lib
            
            data = self._load_data()
            
            if account_uuid not in data:
                logger.warning(f"⚠️ Аккаунт {account_uuid} не найден")
                return False
            
            # Сохраняем резервную копию cookies в отдельный файл
            cookies_backup_file = self.storage_file.parent / "cookies_backup.json"
            try:
                if cookies_backup_file.exists():
                    backup_data = json.load(open(cookies_backup_file, "r", encoding="utf-8"))
                else:
                    backup_data = {}
                
                backup_data[account_uuid] = {
                    "account_uuid": account_uuid,
                    "account_name": data[account_uuid].get("name", "Unknown"),
                    "phone": data[account_uuid].get("phone", ""),
                    "cookies": cookies,
                    "backup_timestamp": datetime.utcnow().isoformat()
                }
                
                with open(cookies_backup_file, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
                logger.debug(f"💾 Резервная копия cookies сохранена для {account_uuid}")
            except Exception as backup_error:
                logger.warning(f"⚠️ Не удалось создать резервную копию cookies: {backup_error}")
            
            data[account_uuid]["cookies"] = cookies
            data[account_uuid]["updated_at"] = datetime.utcnow().isoformat()
            
            self._save_data(data)
            
            # Подсчитываем количество cookies
            cookies_list = json_lib.loads(cookies)
            logger.success(f"🍪 Cookies обновлены для аккаунта {account_uuid}")
            logger.info(f"📊 Сохранено {len(cookies_list)} cookies")
            logger.debug(f"Cookies preview: {cookies[:100]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления cookies: {e}")
            return False
    
    def get_all_accounts(self) -> List[Account]:
        """
        Получение всех аккаунтов.
        
        Returns:
            List[Account]: Список всех аккаунтов
        """
        try:
            data = self._load_data()
            accounts = []
            
            for account_data in data.values():
                account = Account(
                    name=account_data["name"],
                    phone=account_data["phone"],
                    cookies=account_data.get("cookies"),
                    proxy_uuid=account_data.get("proxy_uuid"),
                    uuid=UUID(account_data["uuid"]),
                    created_at=datetime.fromisoformat(account_data["created_at"]) if account_data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(account_data["updated_at"]) if account_data.get("updated_at") else None
                )
                accounts.append(account)
            
            return accounts
            
        except Exception as e:
            logger.error(f"Ошибка получения списка аккаунтов: {e}")
            return []
    
    def update_account(
        self, 
        account_uuid: str, 
        name: Optional[str] = None, 
        phone: Optional[str] = None,
        proxy_uuid: Optional[str] = None
    ) -> bool:
        """
        Обновление данных аккаунта.
        
        Args:
            account_uuid: UUID аккаунта
            name: Новое название (опционально)
            phone: Новый телефон (опционально)
            proxy_uuid: UUID прокси (опционально)
            
        Returns:
            bool: Успешность обновления
        """
        try:
            data = self._load_data()
            account_data = data.get(account_uuid)
            
            if not account_data:
                logger.warning(f"Аккаунт {account_uuid} не найден для обновления")
                return False
            
            # Обновляем только переданные поля
            if name is not None:
                account_data['name'] = name
            if phone is not None:
                account_data['phone'] = phone
            if proxy_uuid is not None:
                account_data['proxy_uuid'] = proxy_uuid
            elif proxy_uuid is None and 'proxy_uuid' in account_data:
                # Удаляем прокси если передано None
                del account_data['proxy_uuid']
            
            # Обновляем время изменения
            account_data['updated_at'] = datetime.now().isoformat()
            
            data[account_uuid] = account_data
            self._save_data(data)
            
            logger.success(f"Аккаунт {account_uuid} обновлен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления аккаунта {account_uuid}: {e}")
            return False
    
    def delete_account(self, account_uuid: str) -> bool:
        """
        Удаление аккаунта.
        
        Args:
            account_uuid: UUID аккаунта
            
        Returns:
            bool: Успешность удаления
        """
        try:
            data = self._load_data()
            
            if account_uuid not in data:
                logger.warning(f"Аккаунт {account_uuid} не найден для удаления")
                return False
            
            account_name = data[account_uuid].get('name', 'Unknown')
            del data[account_uuid]
            self._save_data(data)
            
            logger.success(f"Аккаунт '{account_name}' ({account_uuid}) удален")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления аккаунта {account_uuid}: {e}")
            return False


# Глобальный экземпляр хранилища
account_storage = AccountStorage()

