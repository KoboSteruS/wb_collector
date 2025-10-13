"""
WebSocket endpoints для real-time взаимодействия

Endpoints для авторизации через WebSocket.
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.services import ws_manager, WBAuthService
from app.db import account_storage
from app.models import Account
from app.core import logger


router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/auth/{session_id}")
async def websocket_auth_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint для авторизации аккаунта.
    
    Протокол:
    1. Клиент подключается с session_id
    2. Сервер запускает процесс авторизации
    3. Сервер отправляет статусы через WebSocket
    4. Клиент отправляет код подтверждения
    5. Сервер завершает авторизацию
    
    Args:
        websocket: WebSocket соединение
        session_id: ID сессии авторизации
    """
    session = ws_manager.get_session(session_id)
    
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    await websocket.accept()
    logger.info(f"WebSocket подключен для сессии {session_id}")
    
    try:
        # Запуск процесса авторизации в фоновой задаче
        auth_task = asyncio.create_task(
            _run_authorization(session)
        )
        
        # Обработка входящих сообщений от клиента
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "submit_code":
                    # Получен код от пользователя
                    code = data.get("code", "").strip()
                    if code:
                        logger.info(f"Получен код для сессии {session_id}")
                        session.set_code(code)
                    else:
                        await session.send_message("error", {
                            "message": "Код не может быть пустым"
                        })
                
                elif message_type == "ping":
                    # Проверка соединения
                    await session.send_message("pong", {})
                
                else:
                    logger.warning(f"Неизвестный тип сообщения: {message_type}")
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket отключен для сессии {session_id}")
                break
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")
                break
        
        # Ожидание завершения авторизации
        try:
            await auth_task
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка WebSocket сессии: {e}")
    finally:
        await ws_manager.close_session(session_id)
        logger.info(f"Сессия {session_id} закрыта")


async def _run_authorization(session) -> None:
    """
    Запуск процесса авторизации.
    
    Args:
        session: Сессия авторизации
    """
    try:
        # Создание аккаунта
        account = Account(
            name=session.name,
            phone=session.phone
        )
        
        # Сохранение в БД
        if not account_storage.add_account(account):
            await session.send_message("error", {
                "message": "Ошибка сохранения аккаунта"
            })
            return
        
        await session.send_message("account_created", {
            "account_uuid": str(account.uuid),
            "message": "Аккаунт создан"
        })
        
        # Запуск авторизации через Selenium
        wb_service = WBAuthService(headless=True)
        cookies = await wb_service.login_and_get_cookies_with_ws(
            session.phone,
            session
        )
        
        if cookies:
            # Сохранение cookies
            account_storage.update_cookies(str(account.uuid), cookies)
            
            await session.send_message("completed", {
                "account_uuid": str(account.uuid),
                "message": "Авторизация успешно завершена"
            })
        else:
            await session.send_message("error", {
                "message": "Не удалось получить cookies"
            })
            
    except Exception as e:
        logger.error(f"Ошибка авторизации: {e}")
        await session.send_message("error", {
            "message": f"Ошибка: {str(e)}"
        })


