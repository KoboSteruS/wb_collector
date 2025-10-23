"""
API endpoints для работы с аккаунтами Wildberries

Endpoints для добавления и управления аккаунтами.
"""

from uuid import uuid4
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket
from typing import List

from app.schemas import AccountCreate, AccountResponse, LoginStatus
from app.models import Account
from app.services import WBAuthService, ws_manager
from app.db import account_storage
from app.core import logger


router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("/add_account")
async def add_account(account_data: AccountCreate) -> dict:
    """
    Инициализация процесса добавления аккаунта Wildberries.
    
    Возвращает session_id для подключения к WebSocket.
    
    Процесс:
    1. Создание сессии авторизации
    2. Возврат session_id
    3. Клиент подключается к WebSocket /ws/auth/{session_id}
    4. Через WebSocket происходит весь процесс авторизации
    
    Args:
        account_data: Данные нового аккаунта (название и телефон)
        
    Returns:
        dict: session_id и инструкции для подключения
    """
    from app.services import ws_manager
    
    logger.info(f"Инициализация добавления аккаунта: {account_data.name}")
    
    # Создаем временную WebSocket сессию (будет обновлена при подключении)
    # Здесь мы создаем "заготовку" сессии
    session_id = str(uuid4())
    
    # Сохраняем данные для будущего использования
    temp_session = {
        "session_id": session_id,
        "phone": account_data.phone,
        "name": account_data.name
    }
    
    # Временное хранилище (в продакшене лучше использовать Redis)
    if not hasattr(add_account, '_temp_sessions'):
        add_account._temp_sessions = {}
    add_account._temp_sessions[session_id] = temp_session
    
    logger.info(f"Создана сессия {session_id} для {account_data.name}")
    
    return {
        "session_id": session_id,
        "websocket_url": f"/api/v1/ws/auth/{session_id}",
        "message": "Подключитесь к WebSocket для продолжения авторизации"
    }


@router.get("/list", response_model=List[AccountResponse])
async def list_accounts() -> List[AccountResponse]:
    """
    Получение списка всех аккаунтов.
    
    Returns:
        List[AccountResponse]: Список аккаунтов
    """
    logger.info("Запрос списка аккаунтов")
    
    accounts = account_storage.get_all_accounts()
    
    # Загружаем информацию о прокси
    from app.db.proxy_storage import ProxyStorage
    proxy_storage = ProxyStorage()
    
    result = []
    for acc in accounts:
        proxy_uuid = getattr(acc, 'proxy_uuid', None)
        proxy_name = None
        
        if proxy_uuid:
            proxy = proxy_storage.get_proxy(proxy_uuid)
            if proxy:
                proxy_name = proxy.get('name')
        
        result.append(AccountResponse(
            uuid=str(acc.uuid),
            name=acc.name,
            phone=acc.phone,
            has_cookies=acc.cookies is not None,
            created_at=acc.created_at.isoformat() if acc.created_at else None,
            updated_at=acc.updated_at.isoformat() if acc.updated_at else None,
            proxy_uuid=proxy_uuid,
            proxy_name=proxy_name
        ))
    
    return result


@router.get("/{account_uuid}", response_model=AccountResponse)
async def get_account(account_uuid: str) -> AccountResponse:
    """
    Получение информации об аккаунте по UUID.
    
    Args:
        account_uuid: UUID аккаунта
        
    Returns:
        AccountResponse: Информация об аккаунте
        
    Raises:
        HTTPException: Если аккаунт не найден
    """
    logger.info(f"Запрос аккаунта {account_uuid}")
    
    account = account_storage.get_account(account_uuid)
    
    if not account:
        raise HTTPException(
            status_code=404,
            detail="Аккаунт не найден"
        )
    
    # Загружаем информацию о прокси
    from app.db.proxy_storage import ProxyStorage
    proxy_storage = ProxyStorage()
    
    proxy_uuid = getattr(account, 'proxy_uuid', None)
    proxy_name = None
    
    if proxy_uuid:
        proxy = proxy_storage.get_proxy(proxy_uuid)
        if proxy:
            proxy_name = proxy.get('name')
    
    return AccountResponse(
        uuid=str(account.uuid),
        name=account.name,
        phone=account.phone,
        has_cookies=account.cookies is not None,
        created_at=account.created_at.isoformat() if account.created_at else None,
        updated_at=account.updated_at.isoformat() if account.updated_at else None,
        proxy_uuid=proxy_uuid,
        proxy_name=proxy_name
    )


@router.put("/update/{account_uuid}")
async def update_account(account_uuid: str, account_data: dict) -> dict:
    """
    Обновление данных аккаунта
    
    Args:
        account_uuid: UUID аккаунта
        account_data: Новые данные аккаунта
        
    Returns:
        Результат обновления
    """
    try:
        logger.info(f"Обновление аккаунта: {account_uuid}")
        
        # Проверяем существование аккаунта
        account = account_storage.get_account(account_uuid)
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Аккаунт с UUID {account_uuid} не найден"
            )
        
        # Обновляем данные
        success = account_storage.update_account(
            account_uuid=account_uuid,
            name=account_data.get('name'),
            phone=account_data.get('phone'),
            proxy_uuid=account_data.get('proxy_uuid')
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Не удалось обновить аккаунт"
            )
        
        logger.success(f"Аккаунт {account_uuid} обновлен")
        
        return {
            "success": True,
            "message": f"Аккаунт {account_uuid} успешно обновлен"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обновления аккаунта {account_uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обновления аккаунта: {str(e)}"
        )


@router.delete("/delete/{account_uuid}")
async def delete_account(account_uuid: str) -> dict:
    """
    Удаление аккаунта
    
    Args:
        account_uuid: UUID аккаунта
        
    Returns:
        Результат удаления
    """
    try:
        logger.info(f"Удаление аккаунта: {account_uuid}")
        
        # Проверяем существование аккаунта
        account = account_storage.get_account(account_uuid)
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Аккаунт с UUID {account_uuid} не найден"
            )
        
        # Удаляем аккаунт
        success = account_storage.delete_account(account_uuid)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Не удалось удалить аккаунт"
            )
        
        logger.success(f"Аккаунт {account_uuid} удален")
        
        return {
            "success": True,
            "message": f"Аккаунт {account_uuid} успешно удален"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка удаления аккаунта {account_uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления аккаунта: {str(e)}"
        )

