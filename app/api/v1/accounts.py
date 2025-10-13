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
    
    return [
        AccountResponse(
            uuid=str(acc.uuid),
            name=acc.name,
            phone=acc.phone,
            has_cookies=acc.cookies is not None,
            created_at=acc.created_at.isoformat() if acc.created_at else None,
            updated_at=acc.updated_at.isoformat() if acc.updated_at else None
        )
        for acc in accounts
    ]


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
    
    return AccountResponse(
        uuid=str(account.uuid),
        name=account.name,
        phone=account.phone,
        has_cookies=account.cookies is not None,
        created_at=account.created_at.isoformat() if account.created_at else None,
        updated_at=account.updated_at.isoformat() if account.updated_at else None
    )

