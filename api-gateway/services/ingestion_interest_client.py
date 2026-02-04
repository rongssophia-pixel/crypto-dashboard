"""
Ingestion Interest Client
Calls ingestion-service HTTP control plane to add/remove symbol interest.
"""

import logging
from typing import Optional

import aiohttp

from config import settings

logger = logging.getLogger(__name__)


class IngestionInterestClient:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout_seconds: float = 3.0,
    ):
        self.host = host or settings.ingestion_service_host
        self.port = port or settings.ingestion_service_http_port
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def set_interest(self, *, symbol: str, action: str) -> bool:
        url = f"{self.base_url}/orderbook/interest"
        payload = {"symbol": symbol, "action": action}
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(
                            f"Ingestion interest call failed: status={resp.status} url={url} body={text}"
                        )
                        return False
                    data = await resp.json()
                    return bool(data.get("success", True))
        except Exception as e:
            logger.warning(f"Ingestion interest call error: {e}")
            return False

    async def add(self, symbol: str) -> bool:
        return await self.set_interest(symbol=symbol, action="add")

    async def remove(self, symbol: str) -> bool:
        return await self.set_interest(symbol=symbol, action="remove")


