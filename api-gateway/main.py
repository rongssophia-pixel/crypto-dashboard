"""
API Gateway Main Entry Point
Unified REST API for all services
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from config import settings
# from api import ingestion, analytics, storage, notifications, auth
# from middleware.auth_middleware import verify_token

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crypto Analytics Platform API",
    description="Real-time crypto market data analytics platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": settings.service_name,
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    # TODO: Check connectivity to all downstream services
    return {
        "status": "healthy",
        "services": {
            "ingestion": "unknown",
            "analytics": "unknown",
            "storage": "unknown",
            "notification": "unknown"
        }
    }


# TODO: Include routers from api modules
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
# app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
# app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
# app.include_router(storage.router, prefix="/api/v1/storage", tags=["Storage"])
# app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)

