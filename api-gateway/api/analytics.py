"""
Analytics API Endpoints
Proxy to Analytics Service via gRPC
"""

import logging
import math
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

import grpc
import aiohttp
from config import settings
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from proto import analytics_pb2, analytics_pb2_grpc, common_pb2
from shared.auth.jwt_handler import UserContext
from middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()

# gRPC channel (initialized on first request)
_grpc_channel = None
_grpc_stub = None


def get_analytics_stub() -> analytics_pb2_grpc.AnalyticsServiceStub:
    """Get or create gRPC stub for analytics service"""
    global _grpc_channel, _grpc_stub

    if _grpc_stub is None:
        address = f"{settings.analytics_service_host}:{settings.analytics_service_port}"
        logger.info(f"Connecting to Analytics Service at {address}")
        _grpc_channel = grpc.insecure_channel(address)
        try:
            grpc.channel_ready_future(_grpc_channel).result(timeout=5)
            logger.info("Successfully connected to Analytics Service")
        except grpc.FutureTimeoutError:
            logger.warning(
                f"Connection to Analytics Service at {address} timed out, but proceeding..."
            )

        _grpc_stub = analytics_pb2_grpc.AnalyticsServiceStub(_grpc_channel)

    return _grpc_stub


def close_channel():
    """Close gRPC channel"""
    global _grpc_channel, _grpc_stub
    if _grpc_channel:
        logger.info("Closing Analytics Service gRPC channel")
        _grpc_channel.close()
        _grpc_channel = None
        _grpc_stub = None


def datetime_to_timestamp(dt: datetime) -> common_pb2.Timestamp:
    """Convert datetime to protobuf Timestamp"""
    # Normalize to UTC; treat naive datetimes as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    ts = common_pb2.Timestamp()
    ts.seconds = int(dt.timestamp())
    ts.nanos = int((dt.timestamp() % 1) * 1e9)
    return ts


def timestamp_to_datetime(ts: common_pb2.Timestamp) -> datetime:
    """Convert protobuf Timestamp to datetime"""
    return datetime.fromtimestamp(ts.seconds + ts.nanos / 1e9, tz=timezone.utc)


# ========================================
# REQUEST/RESPONSE MODELS
# ========================================


class MarketDataQuery(BaseModel):
    """Market data query parameters"""

    symbols: List[str]
    start_time: datetime
    end_time: datetime
    limit: int = 1000
    offset: int = 0
    order_by: str = "timestamp_desc"


class CandleQuery(BaseModel):
    """Candle query parameters"""

    symbol: str
    interval: str = "1h"  # 1m, 5m, 15m, 30m, 1h, 4h, 1d
    start_time: datetime
    end_time: datetime
    limit: int = 500


class AggregationQuery(BaseModel):
    """Aggregation query parameters"""

    symbol: str
    metric_types: List[str] = ["avg_price", "total_volume"]
    start_time: datetime
    end_time: datetime
    time_bucket: str = "1h"


class MarketDataPoint(BaseModel):
    """Market data point response"""

    symbol: str
    timestamp: datetime
    price: float
    volume: float
    bid_price: float
    ask_price: float
    metrics: dict = {}


class Candle(BaseModel):
    """OHLCV candle response"""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int


class TimeSeriesPoint(BaseModel):
    """Time series data point"""

    timestamp: datetime
    values: dict


# ========================================
# ENDPOINTS
# ========================================


@router.post("/market-data/query")
async def query_market_data(query: MarketDataQuery):
    """
    Query raw market data

    Calls Analytics Service via gRPC
    """
    try:
        stub = get_analytics_stub()

        # Build gRPC request
        request = analytics_pb2.QueryRequest()
        # request.context.user_id = ... # Inject from middleware
        request.symbols.extend(query.symbols)
        request.start_time.CopyFrom(datetime_to_timestamp(query.start_time))
        request.end_time.CopyFrom(datetime_to_timestamp(query.end_time))
        request.limit = query.limit
        request.offset = query.offset
        request.order_by = query.order_by

        # Call gRPC service
        response = stub.QueryMarketData(request)

        # Transform response
        data = []
        for point in response.data:
            data.append(
                {
                    "symbol": point.symbol,
                    "timestamp": timestamp_to_datetime(point.timestamp).isoformat(),
                    "price": point.price,
                    "volume": point.volume,
                    "bid_price": point.bid_price,
                    "ask_price": point.ask_price,
                    "metrics": dict(point.metrics),
                }
            )

        return {
            "data": data,
            "total_count": response.total_count,
            "has_more": response.has_more,
        }

    except grpc.RpcError as e:
        logger.error(f"gRPC error in query_market_data: {e}")
        raise HTTPException(
            status_code=503, detail=f"Analytics service unavailable: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in query_market_data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/candles/query")
async def query_candles(query: CandleQuery):
    """Query OHLCV candles"""
    try:
        stub = get_analytics_stub()

        # Build gRPC request
        request = analytics_pb2.CandleRequest()
        request.symbol = query.symbol
        request.interval = query.interval
        request.start_time.CopyFrom(datetime_to_timestamp(query.start_time))
        request.end_time.CopyFrom(datetime_to_timestamp(query.end_time))
        request.limit = query.limit

        # Call gRPC service
        response = stub.GetCandles(request)

        # Transform response
        candles = []
        for candle in response.candles:
            candles.append(
                {
                    "timestamp": timestamp_to_datetime(candle.timestamp).isoformat(),
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "trade_count": candle.trade_count,
                }
            )

        return {
            "candles": candles,
            "total_count": response.total_count,
        }

    except grpc.RpcError as e:
        logger.error(f"gRPC error in query_candles: {e}")
        raise HTTPException(
            status_code=503, detail=f"Analytics service unavailable: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in query_candles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    """
    Get latest ticker data with 24h stats
    Proxies to Analytics Service HTTP API
    """
    try:
        url = f"http://{settings.analytics_service_host}:{settings.analytics_service_http_port}/api/v1/ticker/{symbol}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    raise HTTPException(status_code=404, detail=f"Ticker not found for {symbol}")
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching ticker from analytics: {response.status} - {error_text}")
                    raise HTTPException(status_code=response.status, detail="Error fetching ticker data")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_ticker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/candles/{symbol}")
async def get_candles_proxy(
    symbol: str,
    interval: str = Query("1h", description="Candle interval"),
    limit: int = Query(100, description="Number of candles"),
):
    """
    Get candles by interval (simplified)
    Proxies to Analytics Service HTTP API
    """
    try:
        url = f"http://{settings.analytics_service_host}:{settings.analytics_service_http_port}/api/v1/candles/{symbol}"
        params = {"interval": interval, "limit": limit}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching candles from analytics: {response.status} - {error_text}")
                    raise HTTPException(status_code=response.status, detail="Error fetching candle data")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_candles_proxy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/market-data/latest")
async def get_latest_prices(symbols: str = Query(...)):
    """Get latest prices for symbols (comma-separated or multiple params)"""
    try:
        stub = get_analytics_stub()

        # Parse symbols - handle both comma-separated string and list
        if isinstance(symbols, str):
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
        else:
            symbol_list = symbols

        # Build gRPC request - use QueryMarketData with limit=1 per symbol
        # For a more efficient implementation, we'd add a dedicated GetLatestPrices RPC
        results = []

        for symbol in symbol_list:
            request = analytics_pb2.QueryRequest()
            request.symbols.append(symbol)
            # Use a recent time range
            now = datetime.utcnow()
            request.end_time.CopyFrom(datetime_to_timestamp(now))
            request.start_time.CopyFrom(
                datetime_to_timestamp(
                    datetime(now.year, now.month, now.day)  # Start of day
                )
            )
            request.limit = 1
            request.order_by = "timestamp_desc"

            response = stub.QueryMarketData(request)

            if response.data:
                point = response.data[0]
                results.append(
                    {
                        "symbol": point.symbol,
                        "timestamp": timestamp_to_datetime(point.timestamp).isoformat(),
                        "price": point.price,
                        "volume": point.volume,
                        "bid_price": point.bid_price,
                        "ask_price": point.ask_price,
                    }
                )

        # Return "prices" to match frontend expectation
        return {"prices": results}

    except grpc.RpcError as e:
        logger.error(f"gRPC error in get_latest_prices: {e}")
        raise HTTPException(
            status_code=503, detail=f"Analytics service unavailable: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in get_latest_prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metrics/aggregated")
async def get_aggregated_metrics(
    symbol: str,
    metric_types: List[str] = Query(["avg_price", "total_volume"]),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    time_bucket: str = "1h",
):
    """Get aggregated metrics (volatility, avg price, etc.)"""
    try:
        stub = get_analytics_stub()

        # Build gRPC request
        request = analytics_pb2.AggregationRequest()
        request.symbol = symbol
        request.metric_types.extend(metric_types)
        request.start_time.CopyFrom(datetime_to_timestamp(start_time))
        request.end_time.CopyFrom(datetime_to_timestamp(end_time))
        request.time_bucket = time_bucket

        # Call gRPC service
        response = stub.GetAggregatedMetrics(request)

        # Transform response
        time_series = []
        for point in response.time_series:
            values = {}
            for key, value in point.values.items():
                # Replace NaN with None (null in JSON)
                values[key] = None if math.isnan(value) else value
            time_series.append(
                {
                    "timestamp": timestamp_to_datetime(point.timestamp).isoformat(),
                    "values": dict(point.values),
                }
            )

        return {
            "symbol": response.symbol,
            "metrics": dict(response.metrics),
            "time_series": time_series,
        }

    except grpc.RpcError as e:
        logger.error(f"gRPC error in get_aggregated_metrics: {e}")
        raise HTTPException(
            status_code=503, detail=f"Analytics service unavailable: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in get_aggregated_metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/candles")
async def get_candles(
    symbol: str,
    interval: str = "1h",
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    limit: int = 500,
):
    """Get OHLCV candles (GET endpoint)"""
    query = CandleQuery(
        symbol=symbol,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return await query_candles(query)
