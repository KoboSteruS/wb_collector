"""
Утилита для восстановления cookies из резервных копий

Использование:
    python -m app.db.restore_cookies <account_uuid>
    
Или восстановить все:
    python -m app.db.restore_cookies --all
"""

import json
import sys
from pathlib import Path

def restore_cookies_from_backup(account_uuid: str = None, restore_all: bool = False):
    """
    Восстановление cookies из резервной копии.
    
    Args:
        account_uuid: UUID аккаунта для восстановления (или None для всех)
        restore_all: Восстановить все аккаунты из backup
    """
    backup_file = Path("data/cookies_backup.json")
    accounts_file = Path("data/accounts.json")
    
    if not backup_file.exists():
        print(f"❌ Резервная копия не найдена: {backup_file}")
        return False
    
    try:
        # Загружаем резервную копию
        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        
        # Загружаем текущие аккаунты
        if accounts_file.exists():
            with open(accounts_file, "r", encoding="utf-8") as f:
                accounts_data = json.load(f)
        else:
            accounts_data = {}
        
        restored_count = 0
        
        if restore_all:
            # Восстанавливаем все аккаунты
            for uuid, backup_info in backup_data.items():
                if uuid in accounts_data and backup_info.get("cookies"):
                    old_cookies = accounts_data[uuid].get("cookies")
                    accounts_data[uuid]["cookies"] = backup_info["cookies"]
                    accounts_data[uuid]["updated_at"] = backup_info["backup_timestamp"]
                    print(f"✅ Восстановлены cookies для {backup_info.get('account_name', uuid[:8])}")
                    restored_count += 1
        elif account_uuid:
            # Восстанавливаем конкретный аккаунт
            if account_uuid not in backup_data:
                print(f"❌ Аккаунт {account_uuid} не найден в резервной копии")
                return False
            
            if account_uuid not in accounts_data:
                print(f"❌ Аккаунт {account_uuid} не найден в текущих аккаунтах")
                return False
            
            backup_info = backup_data[account_uuid]
            if backup_info.get("cookies"):
                accounts_data[account_uuid]["cookies"] = backup_info["cookies"]
                accounts_data[account_uuid]["updated_at"] = backup_info["backup_timestamp"]
                print(f"✅ Cookies восстановлены для {backup_info.get('account_name', account_uuid[:8])}")
                restored_count = 1
            else:
                print(f"⚠️ В резервной копии нет cookies для {account_uuid}")
                return False
        else:
            print("❌ Укажите account_uuid или используйте --all")
            return False
        
        # Сохраняем обновленные данные
        with open(accounts_file, "w", encoding="utf-8") as f:
            json.dump(accounts_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Восстановлено {restored_count} аккаунт(ов)")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка восстановления: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            restore_cookies_from_backup(restore_all=True)
        else:
            restore_cookies_from_backup(account_uuid=sys.argv[1])
    else:
        print("Использование:")
        print("  python -m app.db.restore_cookies <account_uuid>")
        print("  python -m app.db.restore_cookies --all")


