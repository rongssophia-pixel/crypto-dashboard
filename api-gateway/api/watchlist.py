"""
Watchlist API Endpoints
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from shared.auth.jwt_handler import UserContext
from repositories.watchlist_repository import WatchlistRepository
from middleware.auth_middleware import require_auth
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize repository
watchlist_repo = WatchlistRepository(
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_db,
    user=settings.postgres_user,
    password=settings.postgres_password
)


# ========================================
# Request/Response Models
# ========================================

class WatchlistAddRequest(BaseModel):
    """Request to add a symbol to watchlist"""
    symbol: str


class WatchlistResponse(BaseModel):
    """Response containing user's watchlist"""
    symbols: List[str]


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True


# ========================================
# Watchlist Endpoints
# ========================================

@router.get("", response_model=WatchlistResponse)
async def get_watchlist(current_user: UserContext = Depends(require_auth)):
    """
    Get current user's watchlist
    """
    try:
        symbols = await watchlist_repo.get_watchlist(current_user.user_id)
        return WatchlistResponse(symbols=symbols)
    except Exception as e:
        logger.error(f"Failed to get watchlist for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve watchlist"
        )


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    request: WatchlistAddRequest,
    current_user: UserContext = Depends(require_auth)
):
    """
    Add a symbol to user's watchlist
    """
    try:
        # Basic validation
        symbol = request.symbol.upper()
        if not symbol or len(symbol) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid symbol"
            )

        added = await watchlist_repo.add_to_watchlist(current_user.user_id, symbol)
        
        if added:
            return MessageResponse(message=f"Added {symbol} to watchlist")
        else:
            return MessageResponse(message=f"{symbol} is already in watchlist", success=False)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add to watchlist for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add to watchlist"
        )


@router.delete("/{symbol}", response_model=MessageResponse)
async def remove_from_watchlist(
    symbol: str,
    current_user: UserContext = Depends(require_auth)
):
    """
    Remove a symbol from user's watchlist
    """
    try:
        symbol = symbol.upper()
        removed = await watchlist_repo.remove_from_watchlist(current_user.user_id, symbol)
        
        if removed:
            return MessageResponse(message=f"Removed {symbol} from watchlist")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{symbol} not found in watchlist"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove from watchlist for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove from watchlist"
        )

