"""
Market Data Models
Pydantic models for market data structures
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal


class MarketDataPoint(BaseModel):
    """
    Single market data point (tick)
    """
    tenant_id: str
    symbol: str
    exchange: str
    timestamp: datetime
    price: Decimal = Field(..., decimal_places=8)
    volume: Decimal = Field(..., decimal_places=8)
    bid_price: Optional[Decimal] = Field(None, decimal_places=8)
    ask_price: Optional[Decimal] = Field(None, decimal_places=8)
    bid_volume: Optional[Decimal] = Field(None, decimal_places=8)
    ask_volume: Optional[Decimal] = Field(None, decimal_places=8)
    high_24h: Optional[Decimal] = Field(None, decimal_places=8)
    low_24h: Optional[Decimal] = Field(None, decimal_places=8)
    volume_24h: Optional[Decimal] = Field(None, decimal_places=8)
    price_change_24h: Optional[Decimal] = Field(None, decimal_places=8)
    price_change_pct_24h: Optional[Decimal] = Field(None, decimal_places=4)
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class Candle(BaseModel):
    """
    OHLCV Candle data
    """
    tenant_id: str
    symbol: str
    exchange: str
    interval: str  # 1m, 5m, 15m, 1h, 4h, 1d
    timestamp: datetime
    open: Decimal = Field(..., decimal_places=8)
    high: Decimal = Field(..., decimal_places=8)
    low: Decimal = Field(..., decimal_places=8)
    close: Decimal = Field(..., decimal_places=8)
    volume: Decimal = Field(..., decimal_places=8)
    quote_volume: Optional[Decimal] = Field(None, decimal_places=8)
    trade_count: Optional[int] = None
    taker_buy_volume: Optional[Decimal] = Field(None, decimal_places=8)
    taker_buy_quote_volume: Optional[Decimal] = Field(None, decimal_places=8)
    
    @validator('interval')
    def validate_interval(cls, v):
        """Validate interval format"""
        valid_intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w']
        if v not in valid_intervals:
            raise ValueError(f'Invalid interval: {v}')
        return v
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class MarketDataAggregate(BaseModel):
    """
    Aggregated market data metrics
    """
    tenant_id: str
    symbol: str
    start_time: datetime
    end_time: datetime
    avg_price: Decimal
    min_price: Decimal
    max_price: Decimal
    total_volume: Decimal
    volatility: Optional[Decimal] = None
    price_change_pct: Optional[Decimal] = None
    trade_count: Optional[int] = None
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


# TODO: Add validation for all models
# TODO: Add conversion methods to/from protobuf messages
# TODO: Add conversion methods to/from database records

