"""
WebSocket API Endpoint
Real-time market data streaming via WebSocket
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Request
from pydantic import BaseModel, ValidationError

from config import settings
from services.websocket_manager import ConnectionManager, WS_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketMessage(BaseModel):
    """Base model for WebSocket messages"""
    action: str


class SubscribeMessage(WebSocketMessage):
    """Subscribe to symbols"""
    action: str = "subscribe"
    symbols: list[str]


class UnsubscribeMessage(WebSocketMessage):
    """Unsubscribe from symbols"""
    action: str = "unsubscribe"
    symbols: list[str]


class AuthMessage(WebSocketMessage):
    """Authentication message"""
    action: str = "auth"
    token: str


async def authenticate_websocket(token: Optional[str]) -> Optional[str]:
    """
    Validate JWT token and return user_id
    
    Args:
        token: JWT token string
        
    Returns:
        user_id if valid, None otherwise
    """
    if not token:
        return None
    
    try:
        # TODO: Implement proper JWT verification using shared.auth.jwt_handler
        # For now, use development mode with dummy validation
        
        # Simple validation: token should not be empty
        if token and len(token) > 0:
            # In development mode, extract user_id from token or use default
            # In production, this should verify the JWT signature
            if token == "dev" or token.startswith("dev-"):
                return "dev-user"
            
            # Try to decode as JWT (simplified)
            # Real implementation would use python-jose
            return "authenticated-user"
        
        return None
        
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        return None


async def handle_websocket_message(
    connection_id: str,
    message_data: dict,
    manager: ConnectionManager
):
    """
    Handle incoming WebSocket message from client
    
    Args:
        connection_id: Connection identifier
        message_data: Parsed message data
        manager: Connection manager instance
    """
    action = message_data.get("action")
    
    if not action:
        await manager.send_to_connection(
            connection_id,
            {"type": "error", "message": "Missing 'action' field"}
        )
        return
    
    try:
        if action == "subscribe":
            # Subscribe to symbols
            msg = SubscribeMessage(**message_data)
            subscribed = await manager.subscribe(connection_id, msg.symbols)
            await manager.send_to_connection(
                connection_id,
                {"type": "subscribed", "symbols": subscribed}
            )
            
        elif action == "unsubscribe":
            # Unsubscribe from symbols
            msg = UnsubscribeMessage(**message_data)
            unsubscribed = await manager.unsubscribe(connection_id, msg.symbols)
            await manager.send_to_connection(
                connection_id,
                {"type": "unsubscribed", "symbols": unsubscribed}
            )
            
        elif action == "list_subscriptions":
            # Get current subscriptions
            subscriptions = await manager.get_subscriptions(connection_id)
            await manager.send_to_connection(
                connection_id,
                {"type": "subscriptions", "symbols": subscriptions}
            )
            
        elif action == "ping":
            # Heartbeat
            await manager.send_to_connection(
                connection_id,
                {"type": "pong"}
            )
            
        else:
            await manager.send_to_connection(
                connection_id,
                {"type": "error", "message": f"Unknown action: {action}"}
            )
            
    except ValidationError as e:
        await manager.send_to_connection(
            connection_id,
            {"type": "error", "message": f"Invalid message format: {str(e)}"}
        )
        WS_ERRORS.labels(error_type="validation_error").inc()
        
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await manager.send_to_connection(
            connection_id,
            {"type": "error", "message": "Internal server error"}
        )
        WS_ERRORS.labels(error_type="handler_error").inc()


@router.websocket("/ws/market-data")
async def websocket_market_data(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time market data streaming
    
    Connection:
        ws://localhost:8000/ws/market-data?token=<JWT_TOKEN>
    
    Client Messages:
        - Subscribe: {"action": "subscribe", "symbols": ["BTCUSDT", "ETHUSDT"]}
        - Unsubscribe: {"action": "unsubscribe", "symbols": ["BTCUSDT"]}
        - List subscriptions: {"action": "list_subscriptions"}
        - Ping: {"action": "ping"}
    
    Server Messages:
        - Market data: {"type": "market_data", "symbol": "BTCUSDT", "price": 42150.50, ...}
        - Subscribed: {"type": "subscribed", "symbols": ["BTCUSDT"]}
        - Error: {"type": "error", "message": "..."}
        - Pong: {"type": "pong"}
    """
    # Get connection manager from app state (via websocket.app)
    manager: ConnectionManager = websocket.app.state.ws_manager
    
    # Authenticate
    user_id = await authenticate_websocket(token)
    
    if not user_id:
        # Close connection if authentication fails
        await websocket.close(code=1008, reason="Authentication required")
        WS_ERRORS.labels(error_type="auth_failed").inc()
        logger.warning("WebSocket connection rejected: authentication failed")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Register connection
    connection_id = await manager.connect(websocket, user_id)
    
    try:
        # Send welcome message
        await manager.send_to_connection(
            connection_id,
            {
                "type": "connected",
                "message": "WebSocket connected successfully",
                "connection_id": connection_id,
                "max_subscriptions": settings.websocket_max_subscriptions_per_client
            }
        )
        
        # Main message loop
        while True:
            # Receive message from client
            try:
                raw_message = await websocket.receive_text()
                message_data = json.loads(raw_message)
                
                # Handle message
                await handle_websocket_message(connection_id, message_data, manager)
                
            except json.JSONDecodeError:
                await manager.send_to_connection(
                    connection_id,
                    {"type": "error", "message": "Invalid JSON format"}
                )
                WS_ERRORS.labels(error_type="invalid_json").inc()
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
        
    except RuntimeError as e:
        # Handle RuntimeError from receive_text() when WebSocket is already closed
        if "WebSocket is not connected" in str(e):
            logger.info(f"WebSocket already disconnected: {connection_id}")
        else:
            logger.error(f"WebSocket runtime error for {connection_id}: {e}", exc_info=True)
            WS_ERRORS.labels(error_type="runtime_error").inc()
        
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}", exc_info=True)
        WS_ERRORS.labels(error_type="connection_error").inc()
        
    finally:
        # Clean up connection
        await manager.disconnect(connection_id)


@router.get("/ws/stats")
async def websocket_stats(request: Request):
    """
    Get WebSocket connection statistics
    
    Returns:
        Connection and subscription statistics
    """
    manager: ConnectionManager = request.app.state.ws_manager
    return manager.get_stats()







