"""
Analytics Service Main Entry Point
Real-time query engine for market data
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import proto and shared modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional
from concurrent import futures
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
import grpc

from config import settings
from api.grpc_servicer import AnalyticsServiceServicer
from services.analytics_service import AnalyticsBusinessService
from repositories.clickhouse_repository import ClickHouseRepository
from proto import analytics_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========================================
# PROMETHEUS METRICS
# ========================================
REQUEST_COUNT = Counter(
    'analytics_requests_total',
    'Total analytics requests',
    ['method', 'status']
)
REQUEST_LATENCY = Histogram(
    'analytics_request_latency_seconds',
    'Analytics request latency',
    ['method']
)


# ========================================
# APPLICATION STATE
# ========================================
class AppState:
    """Centralized application state container"""
    # Infrastructure
    clickhouse_repository: ClickHouseRepository = None
    
    # Business service
    analytics_service: AnalyticsBusinessService = None
    
    # Servers
    grpc_server = None


app_state = AppState()


# ========================================
# FASTAPI LIFESPAN
# ========================================
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    FastAPI lifespan context manager
    Manages startup and shutdown of all service resources
    """
    # ========================================
    # STARTUP PHASE
    # ========================================
    logger.info(f"🚀 Starting {settings.service_name}...")
    
    try:
        # 1. Initialize ClickHouse repository
        logger.info("Initializing ClickHouse repository...")
        app_state.clickhouse_repository = ClickHouseRepository(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            database=settings.clickhouse_db,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            secure=settings.clickhouse_secure,
            verify=settings.clickhouse_verify,
        )
        await app_state.clickhouse_repository.connect()
        logger.info("✅ ClickHouse repository initialized")
        
        # 2. Initialize business service
        logger.info("Initializing analytics business service...")
        app_state.analytics_service = AnalyticsBusinessService(
            clickhouse_repository=app_state.clickhouse_repository,
        )
        logger.info("✅ Analytics business service initialized")
        
        # 3. Start gRPC server
        logger.info(f"Starting gRPC server on port {settings.service_port}...")
        app_state.grpc_server = grpc.aio.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=[
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ]
        )
        
        # Add servicer to gRPC server
        analytics_pb2_grpc.add_AnalyticsServiceServicer_to_server(
            AnalyticsServiceServicer(app_state.analytics_service),
            app_state.grpc_server
        )
        
        app_state.grpc_server.add_insecure_port(f"[::]:{settings.service_port}")
        await app_state.grpc_server.start()
        logger.info(f"✅ gRPC server started on port {settings.service_port}")
        
        # Service ready
        logger.info("=" * 60)
        logger.info(f"✅ {settings.service_name} is ready!")
        logger.info(f"   - HTTP/FastAPI: port {settings.http_port}")
        logger.info(f"   - gRPC: port {settings.service_port}")
        logger.info("=" * 60)
        
        # Yield control to the application
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start {settings.service_name}: {e}", exc_info=True)
        raise
    
    finally:
        # ========================================
        # SHUTDOWN PHASE
        # ========================================
        logger.info("=" * 60)
        logger.info(f"🛑 Shutting down {settings.service_name}...")
        logger.info("=" * 60)
        
        # 1. Stop gRPC server
        if app_state.grpc_server:
            try:
                logger.info("Stopping gRPC server...")
                await app_state.grpc_server.stop(grace=5.0)
                logger.info("✅ gRPC server stopped")
            except Exception as e:
                logger.error(f"Error stopping gRPC server: {e}")
        
        # 2. Close ClickHouse connection
        if app_state.clickhouse_repository:
            try:
                logger.info("Closing ClickHouse connection...")
                await app_state.clickhouse_repository.disconnect()
                logger.info("✅ ClickHouse connection closed")
            except Exception as e:
                logger.error(f"Error closing ClickHouse connection: {e}")
        
        logger.info("=" * 60)
        logger.info(f"✅ {settings.service_name} shutdown complete")
        logger.info("=" * 60)


# ========================================
# CREATE FASTAPI APP
# ========================================
app = FastAPI(
    title="Crypto Analytics Service",
    description="Real-time query engine for crypto market data",
    version="1.0.0",
    lifespan=lifespan,
)


# ========================================
# DEPENDENCY INJECTION
# ========================================
def get_analytics_service() -> AnalyticsBusinessService:
    """Dependency injection for analytics business service"""
    if app_state.analytics_service is None:
        raise RuntimeError("Analytics service not initialized")
    return app_state.analytics_service


# ========================================
# HTTP ENDPOINTS (Monitoring & REST API)
# ========================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
        "description": "Real-time crypto market data analytics service"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and orchestration
    Used by Kubernetes liveness/readiness probes
    """
    health_status = {
        "service": settings.service_name,
        "status": "healthy",
        "checks": {
            "grpc_server": app_state.grpc_server is not None,
            "analytics_service": app_state.analytics_service is not None,
            "clickhouse": app_state.clickhouse_repository is not None,
        }
    }
    
    # Check ClickHouse connection
    if app_state.clickhouse_repository:
        try:
            stats = app_state.clickhouse_repository.get_stats()
            health_status["checks"]["clickhouse_connected"] = stats.get("connected", False)
        except Exception:
            health_status["checks"]["clickhouse_connected"] = False
    
    # Determine overall health
    all_healthy = all(health_status["checks"].values())
    health_status["status"] = "healthy" if all_healthy else "degraded"
    
    return health_status


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    Exposes service metrics for monitoring
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    if app_state.analytics_service:
        return app_state.analytics_service.get_stats()
    return {"error": "Service not initialized"}


# ========================================
# REST API ENDPOINTS (HTTP alternatives to gRPC)
# ========================================

@app.get("/api/v1/market-data/latest")
async def get_latest_prices(
    symbols: List[str] = Query(..., description="List of trading symbols"),
    tenant_id: str = Query("", description="Tenant identifier")
):
    """
    Get latest prices for specified symbols
    
    HTTP alternative to gRPC for simple queries
    """
    try:
        service = get_analytics_service()
        with REQUEST_LATENCY.labels(method="get_latest_prices").time():
            result = await service.get_latest_prices(
                symbols=symbols,
            )
        REQUEST_COUNT.labels(method="get_latest_prices", status="success").inc()
        return {"data": result}
    except ValueError as e:
        REQUEST_COUNT.labels(method="get_latest_prices", status="error").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        REQUEST_COUNT.labels(method="get_latest_prices", status="error").inc()
        logger.error(f"Error in get_latest_prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/candles")
async def get_candles(
    symbol: str = Query(..., description="Trading symbol"),
    interval: str = Query("1h", description="Candle interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)"),
    start_time: datetime = Query(..., description="Start timestamp"),
    end_time: datetime = Query(..., description="End timestamp"),
    limit: int = Query(500, description="Maximum candles to return"),
    tenant_id: str = Query("", description="Tenant identifier")
):
    """
    Get OHLCV candles for a symbol
    
    HTTP alternative to gRPC GetCandles
    """
    try:
        service = get_analytics_service()
        with REQUEST_LATENCY.labels(method="get_candles").time():
            result = await service.get_candles(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        REQUEST_COUNT.labels(method="get_candles", status="success").inc()
        return result
    except ValueError as e:
        REQUEST_COUNT.labels(method="get_candles", status="error").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        REQUEST_COUNT.labels(method="get_candles", status="error").inc()
        logger.error(f"Error in get_candles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/metrics/aggregated")
async def get_aggregated_metrics(
    symbol: str = Query(..., description="Trading symbol"),
    metric_types: List[str] = Query(
        ["avg_price", "total_volume"], 
        description="Metrics to calculate"
    ),
    start_time: datetime = Query(..., description="Start timestamp"),
    end_time: datetime = Query(..., description="End timestamp"),
    time_bucket: str = Query("1h", description="Time bucket (1h, 4h, 1d, 1w)"),
    tenant_id: str = Query("", description="Tenant identifier")
):
    """
    Get aggregated metrics (volatility, VWAP, etc.)
    
    HTTP alternative to gRPC GetAggregatedMetrics
    """
    try:
        service = get_analytics_service()
        with REQUEST_LATENCY.labels(method="get_aggregated_metrics").time():
            result = await service.get_aggregated_metrics(
                symbol=symbol,
                metric_types=metric_types,
                start_time=start_time,
                end_time=end_time,
                time_bucket=time_bucket,
            )
        REQUEST_COUNT.labels(method="get_aggregated_metrics", status="success").inc()
        return result
    except ValueError as e:
        REQUEST_COUNT.labels(method="get_aggregated_metrics", status="error").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        REQUEST_COUNT.labels(method="get_aggregated_metrics", status="error").inc()
        logger.error(f"Error in get_aggregated_metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    tenant_id: str = Query("", description="Tenant identifier")
):
    """
    Get latest ticker data with 24h stats
    """
    try:
        service = get_analytics_service()
        with REQUEST_LATENCY.labels(method="get_ticker").time():
            result = await service.get_ticker_data(symbol)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Ticker not found for {symbol}")
            
        REQUEST_COUNT.labels(method="get_ticker", status="success").inc()
        return result
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(method="get_ticker", status="error").inc()
        logger.error(f"Error in get_ticker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/candles/{symbol}")
async def get_candles_simple(
    symbol: str,
    interval: str = Query("1h", description="Candle interval"),
    limit: int = Query(100, description="Number of candles"),
    tenant_id: str = Query("", description="Tenant identifier")
):
    """
    Get candles by interval (simplified endpoint)
    """
    try:
        service = get_analytics_service()
        with REQUEST_LATENCY.labels(method="get_candles_simple").time():
            result = await service.get_candles_by_interval(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
        REQUEST_COUNT.labels(method="get_candles_simple", status="success").inc()
        return result
    except ValueError as e:
        REQUEST_COUNT.labels(method="get_candles_simple", status="error").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        REQUEST_COUNT.labels(method="get_candles_simple", status="error").inc()
        logger.error(f"Error in get_candles_simple: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/market-data/query")
async def query_market_data(
    symbols: List[str] = Query(..., description="List of trading symbols"),
    start_time: datetime = Query(..., description="Start timestamp"),
    end_time: datetime = Query(..., description="End timestamp"),
    limit: int = Query(1000, description="Maximum records to return"),
    offset: int = Query(0, description="Pagination offset"),
    order_by: str = Query("timestamp_desc", description="Sort order"),
    tenant_id: str = Query("", description="Tenant identifier")
):
    """
    Query raw market data
    
    HTTP alternative to gRPC QueryMarketData
    """
    try:
        service = get_analytics_service()
        with REQUEST_LATENCY.labels(method="query_market_data").time():
            result = await service.query_market_data(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset,
                order_by=order_by,
            )
        REQUEST_COUNT.labels(method="query_market_data", status="success").inc()
        return result
    except ValueError as e:
        REQUEST_COUNT.labels(method="query_market_data", status="error").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        REQUEST_COUNT.labels(method="query_market_data", status="error").inc()
        logger.error(f"Error in query_market_data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ========================================
# RUN THE APP
# ========================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.http_port,
        log_level="info",
        access_log=True,
    )
