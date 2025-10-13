"""
WebSocket роутер для авторизации

Упрощенная версия WebSocket endpoint.
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import ws_manager, WBAuthService
from app.db import account_storage
from app.models import Account
from app.core import logger


router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/auth/{session_id}")
async def websocket_auth(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint для авторизации.
    
    Протокол обмена сообщениями:
    
    От сервера к клиенту:
    - {"type": "status", "data": {"step": "...", "message": "..."}}
    - {"type": "account_created", "data": {"account_uuid": "..."}}
    - {"type": "completed", "data": {"account_uuid": "...", "message": "..."}}
    - {"type": "error", "data": {"message": "..."}}
    
    От клиента к серверу:
    - {"type": "submit_code", "code": "1234"}
    - {"type": "ping"}
    
    Args:
        websocket: WebSocket соединение
        session_id: ID сессии
    """
    # Получаем данные сессии из временного хранилища
    from app.api.v1.accounts import add_account
    
    if not hasattr(add_account, '_temp_sessions'):
        await websocket.close(code=1008, reason="Session not found")
        return
    
    temp_session = add_account._temp_sessions.get(session_id)
    if not temp_session:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    await websocket.accept()
    logger.info(f"WebSocket подключен: {session_id}")
    
    # Создаем полноценную сессию
    session = ws_manager.create_session(
        websocket,
        temp_session["phone"],
        temp_session["name"]
    )
    
    # Удаляем временные данные
    del add_account._temp_sessions[session_id]
    
    try:
        # Запуск авторизации в фоне
        auth_task = asyncio.create_task(_run_auth(session))
        
        # Обработка сообщений от клиента
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                
                if msg_type == "submit_code":
                    code = data.get("code", "").strip()
                    if code:
                        logger.info(f"Получен код: {code}")
                        session.set_code(code)
                    else:
                        await session.send_message("error", {
                            "message": "Код не может быть пустым"
                        })
                
                elif msg_type == "ping":
                    await session.send_message("pong", {})
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket отключен: {session_id}")
                break
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                break
        
        try:
            await auth_task
        except:
            pass
            
    finally:
        await ws_manager.close_session(session.session_id)


async def _run_auth(session):
    """Выполнение авторизации"""
    try:
        # Создание аккаунта
        account = Account(name=session.name, phone=session.phone)
        
        if not account_storage.add_account(account):
            await session.send_message("error", {
                "message": "Ошибка сохранения аккаунта"
            })
            return
        
        await session.send_message("account_created", {
            "account_uuid": str(account.uuid)
        })
        
        # Авторизация через Selenium
        wb_service = WBAuthService(headless=True)
        cookies = await wb_service.login_and_get_cookies_with_ws(
            session.phone,
            session
        )
        
        if cookies:
            account_storage.update_cookies(str(account.uuid), cookies)
            await session.send_message("completed", {
                "account_uuid": str(account.uuid),
                "message": "Авторизация завершена"
            })
        else:
            await session.send_message("error", {
                "message": "Не удалось получить cookies"
            })
            
    except Exception as e:
        logger.error(f"Ошибка авторизации: {e}")
        await session.send_message("error", {"message": str(e)})


