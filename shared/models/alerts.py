"""
Alert Models
Pydantic models for alert subscriptions and events
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum


class ConditionType(str, Enum):
    """Alert condition types"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    VOLUME_SPIKE = "volume_spike"
    PRICE_CHANGE_PCT = "price_change_pct"
    VOLATILITY_HIGH = "volatility_high"


class ComparisonOperator(str, Enum):
    """Comparison operators for alert conditions"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="


class AlertSubscription(BaseModel):
    """
    Alert subscription configuration
    """
    id: Optional[str] = None
    tenant_id: str
    user_id: str
    ticker_symbol: str
    condition_type: ConditionType
    threshold_value: Decimal = Field(..., decimal_places=8)
    comparison_operator: ComparisonOperator = ComparisonOperator.GREATER_THAN
    timeframe_minutes: Optional[int] = None
    is_active: bool = True
    notification_channels: List[str] = Field(default_factory=lambda: ["email"])
    cooldown_minutes: int = 60
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class AlertEvent(BaseModel):
    """
    Triggered alert event
    """
    tenant_id: str
    timestamp: datetime
    alert_id: str
    user_id: str
    symbol: str
    condition_type: ConditionType
    threshold_value: Decimal = Field(..., decimal_places=8)
    triggered_value: Decimal = Field(..., decimal_places=8)
    comparison_operator: ComparisonOperator
    message: str
    metadata: Optional[dict] = None
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


# TODO: Add alert evaluation logic
# TODO: Add cooldown period checking
# TODO: Add conversion to notification messages

