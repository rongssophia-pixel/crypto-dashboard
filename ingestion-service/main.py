"""
Ingestion Service Main Entry Point
Automatically ingests market data from Binance for all USDT trading pairs
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import proto and shared modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from config import settings
from services.ingestion_service import IngestionBusinessService
from services.orderbook_ingestion_service import OrderbookIngestionService
from repositories.kafka_repository import KafkaRepository
from connectors.binance_connector import BinanceConnector
from shared.kafka_utils.producer import KafkaProducerWrapper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AppState:
    """Centralized application state container"""
    # Infrastructure resources
    kafka_producer: KafkaProducerWrapper = None
    binance_connector: BinanceConnector = None
    
    # Repositories
    kafka_repository: KafkaRepository = None
    
    # Business service
    ingestion_service: IngestionBusinessService = None
    orderbook_ingestion_service: OrderbookIngestionService = None


app_state = AppState()


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
        # 1. Initialize Kafka producer
        logger.info("Initializing Kafka producer...")
        app_state.kafka_producer = KafkaProducerWrapper(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id=f"{settings.service_name}-producer",
            security_protocol=settings.kafka_security_protocol,
            sasl_mechanism=settings.kafka_sasl_mechanism,
            sasl_plain_username=settings.kafka_sasl_username,
            sasl_plain_password=settings.kafka_sasl_password,
        )
        logger.info("✅ Kafka producer initialized")
        
        # 2. Initialize Binance connector
        logger.info("Initializing Binance connector...")
        app_state.binance_connector = BinanceConnector(
            websocket_url=settings.binance_websocket_url,
            api_key=settings.binance_api_key,
            api_secret=settings.binance_api_secret,
        )
        # Update REST API URL if configured
        app_state.binance_connector.rest_base_url = settings.binance_rest_api_url
        logger.info("✅ Binance connector initialized")
        
        # 3. Initialize repositories
        logger.info("Initializing repositories...")
        app_state.kafka_repository = KafkaRepository(app_state.kafka_producer)
        logger.info("✅ Repositories initialized")
        
        # 4. Initialize business service
        logger.info("Initializing ingestion business service...")
        app_state.ingestion_service = IngestionBusinessService(
            kafka_repository=app_state.kafka_repository,
            binance_connector=app_state.binance_connector,
        )
        logger.info("✅ Ingestion business service initialized")

        # 4b. Initialize subscription-driven orderbook ingestion service
        logger.info("Initializing orderbook ingestion service...")
        app_state.orderbook_ingestion_service = OrderbookIngestionService(
            kafka_repository=app_state.kafka_repository,
            binance_connector=app_state.binance_connector,
        )
        logger.info("✅ Orderbook ingestion service initialized")
        
        # 5. Start automatic ingestion if enabled
        if settings.auto_start_ingestion:
            logger.info("\n" + "=" * 70)
            logger.info("🤖 AUTO-START INGESTION ENABLED")
            logger.info("=" * 70)
            
            result = await app_state.ingestion_service.start_auto_ingestion(
                intervals=settings.kline_interval_list,
                quote_currency=settings.symbol_filter_quote_currency,
                enable_ticker=settings.enable_ticker_streams,
                max_symbols_per_connection=settings.max_symbols_per_connection,
                kafka_topic=settings.kafka_topic_raw_market_data,
            )
            
            if result.get("success"):
                logger.info("✅ Automatic ingestion started successfully")
                
                # 6. Start background symbol refresh task
                if settings.symbol_refresh_interval_hours > 0:
                    await app_state.ingestion_service.start_symbol_refresh_task(
                        refresh_interval_hours=settings.symbol_refresh_interval_hours,
                        intervals=settings.kline_interval_list,
                        quote_currency=settings.symbol_filter_quote_currency,
                        enable_ticker=settings.enable_ticker_streams,
                        max_symbols_per_connection=settings.max_symbols_per_connection,
                        kafka_topic=settings.kafka_topic_raw_market_data,
                    )
                    logger.info(
                        f"✅ Symbol refresh task started "
                        f"(refresh every {settings.symbol_refresh_interval_hours}h)"
                    )
            else:
                logger.error(
                    f"❌ Failed to start automatic ingestion: {result.get('error')}"
                )
        else:
            logger.warning("⚠️  Auto-start ingestion is DISABLED")
        
        # Service ready
        logger.info("\n" + "=" * 70)
        logger.info(f"✅ {settings.service_name} is READY!")
        logger.info(f"   - HTTP/FastAPI: port {settings.http_port}")
        logger.info(f"   - Kafka topic: {settings.kafka_topic_raw_market_data}")
        logger.info(f"   - Kline intervals: {', '.join(settings.kline_interval_list)}")
        logger.info(f"   - Ticker streams: {'enabled' if settings.enable_ticker_streams else 'disabled'}")
        logger.info("=" * 70 + "\n")
        
        # Yield control to the application
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start {settings.service_name}: {e}", exc_info=True)
        raise
    
    finally:
        # ========================================
        # SHUTDOWN PHASE
        # ========================================
        logger.info("\n" + "=" * 70)
        logger.info(f"🛑 Shutting down {settings.service_name}...")
        logger.info("=" * 70)
        
        # 1. Stop ingestion service
        if app_state.ingestion_service:
            try:
                logger.info("Stopping ingestion service...")
                await app_state.ingestion_service.stop_auto_ingestion()
                logger.info("✅ Ingestion service stopped")
            except Exception as e:
                logger.error(f"Error stopping ingestion service: {e}")
        
        # 2. Close Binance connector
        if app_state.binance_connector:
            try:
                logger.info("Closing Binance connector...")
                await app_state.binance_connector.close()
                logger.info("✅ Binance connector closed")
            except Exception as e:
                logger.error(f"Error closing Binance connector: {e}")
        
        # 3. Close Kafka producer
        if app_state.kafka_producer:
            try:
                logger.info("Closing Kafka producer...")
                app_state.kafka_producer.flush(timeout=10)
                app_state.kafka_producer.close()
                logger.info("✅ Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
        
        logger.info("=" * 70)
        logger.info(f"✅ {settings.service_name} shutdown complete")
        logger.info("=" * 70 + "\n")


# ========================================
# CREATE FASTAPI APP
# ========================================
app = FastAPI(
    title="Crypto Ingestion Service",
    description="Automatic crypto market data ingestion from Binance",
    version="2.0.0",
    lifespan=lifespan,
)


# ========================================
# HTTP ENDPOINTS (Monitoring & Status)
# ========================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": "2.0.0",
        "status": "running",
        "description": "Automatic crypto market data ingestion service",
        "mode": "auto-ingestion",
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
            "ingestion_service": app_state.ingestion_service is not None,
            "kafka_producer": app_state.kafka_producer is not None,
            "binance_connector": app_state.binance_connector is not None,
        }
    }
    
    # Add ingestion status
    if app_state.ingestion_service:
        status = app_state.ingestion_service.get_status()
        health_status["ingestion"] = status
    
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


@app.get("/status")
async def get_status():
    """
    Get detailed ingestion status
    """
    if app_state.ingestion_service:
        status = app_state.ingestion_service.get_status()
    else:
        status = {"error": "Service not initialized"}

    # Add orderbook ingestion status if available
    if app_state.orderbook_ingestion_service:
        status["orderbook"] = app_state.orderbook_ingestion_service.get_status()
    return status


from pydantic import BaseModel


class OrderbookInterestRequest(BaseModel):
    symbol: str
    action: str  # add | remove


@app.post("/orderbook/interest")
async def orderbook_interest(req: OrderbookInterestRequest):
    """
    Control plane endpoint for API Gateway:
      - action=add: start/retain orderbook ingestion for symbol
      - action=remove: stop orderbook ingestion when no viewers remain
    """
    if not app_state.orderbook_ingestion_service:
        return {"success": False, "error": "Orderbook ingestion not initialized"}
    return await app_state.orderbook_ingestion_service.set_interest(
        symbol=req.symbol, action=req.action
    )


@app.get("/orderbook/interest")
async def orderbook_interest_status():
    """Debug endpoint to inspect current orderbook interest/refcounts."""
    if not app_state.orderbook_ingestion_service:
        return {"success": False, "error": "Orderbook ingestion not initialized"}
    return {"success": True, **app_state.orderbook_ingestion_service.get_status()}


# ========================================
# RUN THE APP
# ========================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.http_port,
        log_level="info",
        access_log=True,
    )
