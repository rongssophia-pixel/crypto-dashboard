"""
Orderbook WebSocket API Endpoint
Real-time depth snapshots for a single symbol.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Request
from pydantic import BaseModel, ValidationError

from config import settings
from api.websocket import authenticate_websocket
from services.orderbook_connection_manager import OrderbookConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketMessage(BaseModel):
    action: str


class SubscribeMessage(WebSocketMessage):
    action: str = "subscribe"
    symbols: list[str]


class UnsubscribeMessage(WebSocketMessage):
    action: str = "unsubscribe"
    symbols: list[str]


async def handle_message(connection_id: str, message_data: dict, manager: OrderbookConnectionManager):
    action = message_data.get("action")
    if not action:
        await manager.send_to_connection(connection_id, {"type": "error", "message": "Missing 'action' field"})
        return

    try:
        if action == "subscribe":
            msg = SubscribeMessage(**message_data)
            subscribed = await manager.subscribe(connection_id, msg.symbols)
            await manager.send_to_connection(connection_id, {"type": "subscribed", "symbols": subscribed})

        elif action == "unsubscribe":
            msg = UnsubscribeMessage(**message_data)
            unsubscribed = await manager.unsubscribe(connection_id, msg.symbols)
            await manager.send_to_connection(connection_id, {"type": "unsubscribed", "symbols": unsubscribed})

        elif action == "list_subscriptions":
            subs = await manager.get_subscriptions(connection_id)
            await manager.send_to_connection(connection_id, {"type": "subscriptions", "symbols": subs})

        elif action == "ping":
            await manager.send_to_connection(connection_id, {"type": "pong"})

        else:
            await manager.send_to_connection(connection_id, {"type": "error", "message": f"Unknown action: {action}"})

    except ValidationError as e:
        await manager.send_to_connection(connection_id, {"type": "error", "message": f"Invalid message format: {str(e)}"})

    except Exception as e:
        logger.error(f"Error handling orderbook WS message: {e}", exc_info=True)
        await manager.send_to_connection(connection_id, {"type": "error", "message": "Internal server error"})


@router.websocket("/ws/orderbook")
async def websocket_orderbook(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint for real-time orderbook snapshots.

    Connection:
      ws://localhost:8000/ws/orderbook?token=<JWT_TOKEN>
    """
    manager: OrderbookConnectionManager = websocket.app.state.orderbook_ws_manager

    user_id = await authenticate_websocket(token)
    if not user_id:
        await websocket.close(code=1008, reason="Authentication required")
        return

    await websocket.accept()
    connection_id = await manager.connect(websocket, user_id)

    try:
        await manager.send_to_connection(
            connection_id,
            {
                "type": "connected",
                "message": "Orderbook WebSocket connected successfully",
                "connection_id": connection_id,
                "max_subscriptions": 1,
            },
        )

        while True:
            raw_message = await websocket.receive_text()
            message_data = json.loads(raw_message)
            await handle_message(connection_id, message_data, manager)

    except WebSocketDisconnect:
        logger.info(f"Orderbook WebSocket disconnected: {connection_id}")

    except RuntimeError as e:
        if "WebSocket is not connected" in str(e):
            logger.info(f"Orderbook WebSocket already disconnected: {connection_id}")
        else:
            logger.error(f"Orderbook WebSocket runtime error: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Orderbook WebSocket error: {e}", exc_info=True)

    finally:
        await manager.disconnect(connection_id)


@router.get("/ws/orderbook/stats")
async def orderbook_ws_stats(request: Request):
    manager: OrderbookConnectionManager = request.app.state.orderbook_ws_manager
    return manager.get_stats()


