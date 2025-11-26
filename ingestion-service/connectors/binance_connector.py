"""
Binance Connector
WebSocket and REST API client for Binance exchange
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import websockets

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BinanceConnector:
    """
    Connector for Binance exchange
    Handles WebSocket streams and REST API calls
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        websocket_url: str = "wss://stream.binance.com:9443",
    ):
        """
        Initialize Binance connector

        Args:
            api_key: Binance API key (optional, for private endpoints)
            api_secret: Binance API secret (optional, for private endpoints)
            websocket_url: WebSocket base URL
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.websocket_url = websocket_url
        self.rest_base_url = "https://api.binance.com"
        self.active_connections = {}
        logger.info("BinanceConnector initialized")

    async def start_ticker_stream(
        self, symbols: List[str], callback: Callable[[Dict[str, Any]], None]
    ) -> str:
        """
        Start WebSocket stream for ticker data

        Args:
            symbols: List of trading symbols (e.g., ['BTCUSDT', 'ETHUSDT'])
            callback: Function to call with each message

        Returns:
            Stream connection ID
        """
        # TODO: Implement ticker stream
        # 1. Format symbols for Binance WebSocket (lowercase)
        # 2. Build WebSocket URL with streams
        # 3. Connect and start receiving messages
        # 4. Parse and normalize data
        # 5. Call callback for each message
        # 6. Handle reconnection on disconnect
        """Start WebSocket stream for 24hr ticker data"""
        connection_id = str(uuid.uuid4())

        # Format symbols for Binance (lowercase)
        streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
        stream_names = "/".join(streams)

        # Combined stream URL
        url = f"{self.websocket_url}/stream?streams={stream_names}"

        # Start WebSocket handler task
        task = asyncio.create_task(
            self._websocket_handler(url, callback, connection_id, "ticker")
        )
        self.active_connections[connection_id] = task

        logger.info(f"Started ticker stream for {symbols}: {connection_id}")
        return connection_id

    async def start_trade_stream(
        self, symbols: List[str], callback: Callable[[Dict[str, Any]], None]
    ) -> str:
        """
        Start WebSocket stream for trade data

        Args:
            symbols: List of trading symbols
            callback: Function to call with each message

        Returns:
            Stream connection ID
        """
        # TODO: Implement trade stream
        """Start WebSocket stream for trade data"""
        connection_id = str(uuid.uuid4())

        # Format symbols for Binance (lowercase)
        streams = [f"{symbol.lower()}@trade" for symbol in symbols]
        stream_names = "/".join(streams)

        url = f"{self.websocket_url}/stream?streams={stream_names}"

        task = asyncio.create_task(
            self._websocket_handler(url, callback, connection_id, "trade")
        )
        self.active_connections[connection_id] = task

        logger.info(f"Started trade stream for {symbols}: {connection_id}")
        return connection_id

    async def start_kline_stream(
        self,
        symbols: List[str],
        interval: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> str:
        """
        Start WebSocket stream for candlestick data

        Args:
            symbols: List of trading symbols
            interval: Kline interval (1m, 5m, 1h, etc.)
            callback: Function to call with each message

        Returns:
            Stream connection ID
        """
        # TODO: Implement kline stream
        connection_id = str(uuid.uuid4())

        # Format symbols for Binance (lowercase)
        # intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
        streams = [f"{symbol.lower()}@kline_{interval}" for symbol in symbols]
        stream_names = "/".join(streams)

        url = f"{self.websocket_url}/stream?streams={stream_names}"

        task = asyncio.create_task(
            self._websocket_handler(url, callback, connection_id, "kline")
        )
        self.active_connections[connection_id] = task

        logger.info(f"Started kline stream for {symbols} ({interval}): {connection_id}")
        return connection_id

    async def stop_stream(self, connection_id: str) -> bool:
        """
        Stop an active WebSocket stream

        Args:
            connection_id: Stream connection ID

        Returns:
            True if stopped successfully
        """
        # TODO: Implement stream stop
        # 1. Find active connection
        # 2. Close WebSocket
        # 3. Remove from active connections
        if connection_id in self.active_connections:
            task = self.active_connections[connection_id]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            del self.active_connections[connection_id]
            logger.info(f"Stopped stream: {connection_id}")
            return True

        logger.warning(f"Stream not found: {connection_id}")
        return False

    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical candlestick data via REST API

        Args:
            symbol: Trading symbol
            interval: Kline interval
            start_time: Start timestamp (milliseconds)
            end_time: End timestamp (milliseconds)
            limit: Number of candles to fetch (max 1000)

        Returns:
            List of OHLCV candles
        """
        # TODO: Implement historical data fetch
        # 1. Build request URL with parameters
        # 2. Make HTTP GET request with aiohttp
        # 3. Parse response
        # 4. Transform to standard format
        # 5. Return candles
        """Fetch historical candlestick data via REST API"""
        endpoint = f"{self.rest_base_url}/api/v3/klines"

        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000),  # Binance max is 1000
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # Transform to standard format
                    candles = []
                    for item in data:
                        candles.append(
                            {
                                "timestamp": item[0],
                                "open": float(item[1]),
                                "high": float(item[2]),
                                "low": float(item[3]),
                                "close": float(item[4]),
                                "volume": float(item[5]),
                                "close_time": item[6],
                                "quote_volume": float(item[7]),
                                "trade_count": item[8],
                                "taker_buy_volume": float(item[9]),
                                "taker_buy_quote_volume": float(item[10]),
                            }
                        )

                    logger.info(f"Fetched {len(candles)} candles for {symbol}")
                    return candles
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to fetch klines: {response.status} - {error_text}"
                    )
                    return []

    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get exchange trading rules and symbol information

        Args:
            symbol: Optional specific symbol

        Returns:
            Exchange info dictionary
        """
        # TODO: Implement exchange info fetch
        endpoint = f"{self.rest_base_url}/api/v3/exchangeInfo"

        params = {}
        if symbol:
            params["symbol"] = symbol.upper()

        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Fetched exchange info")
                    return data
                else:
                    logger.error(f"Failed to fetch exchange info: {response.status}")
                    return {}

    def _normalize_ticker_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Binance ticker data to standard format

        Args:
            raw_data: Raw data from Binance WebSocket

        Returns:
            Normalized data dictionary
        """
        # TODO: Implement data normalization
        data = raw_data.get("data", {})

        return {
            "symbol": data.get("s"),
            "price": float(data.get("c", 0)),
            "volume": float(data.get("v", 0)),
            "bid_price": float(data.get("b", 0)),
            "ask_price": float(data.get("a", 0)),
            "bid_volume": float(data.get("B", 0)),
            "ask_volume": float(data.get("A", 0)),
            "high_24h": float(data.get("h", 0)),
            "low_24h": float(data.get("l", 0)),
            "volume_24h": float(data.get("v", 0)),
            "price_change_24h": float(data.get("p", 0)),
            "price_change_pct_24h": float(data.get("P", 0)),
            "trade_count": int(data.get("n", 0)),
            "timestamp": data.get("E", int(datetime.utcnow().timestamp() * 1000)),
            "exchange": "binance",
        }

    def _normalize_trade_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Binance trade data to standard format"""
        data = raw_data.get("data", {})

        return {
            "symbol": data.get("s"),
            "price": float(data.get("p", 0)),
            "volume": float(data.get("q", 0)),
            "timestamp": data.get("T", int(datetime.utcnow().timestamp() * 1000)),
            "trade_id": data.get("t"),
            "is_buyer_maker": data.get("m"),
            "exchange": "binance",
        }

    def _normalize_kline_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Binance kline data to standard format"""
        data = raw_data.get("data", {})
        kline = data.get("k", {})

        return {
            "symbol": kline.get("s"),
            "interval": kline.get("i"),
            "timestamp": kline.get("t"),
            "open": float(kline.get("o", 0)),
            "high": float(kline.get("h", 0)),
            "low": float(kline.get("l", 0)),
            "close": float(kline.get("c", 0)),
            "volume": float(kline.get("v", 0)),
            "close_time": kline.get("T"),
            "quote_volume": float(kline.get("q", 0)),
            "trade_count": int(kline.get("n", 0)),
            "is_closed": kline.get("x", False),
            "exchange": "binance",
        }

    async def _websocket_handler(
        self,
        url: str,
        callback: Callable[[Dict[str, Any]], None],
        connection_id: str,
        stream_type: str,
    ):
        """
        Handle WebSocket connection and messages

        Args:
            url: WebSocket URL
            callback: Callback function for messages
            connection_id: Connection identifier
        """
        # TODO: Implement WebSocket handler
        # 1. Connect to WebSocket
        # 2. Listen for messages
        # 3. Parse JSON
        # 4. Call callback
        # 5. Handle errors and reconnection
        reconnect_delay = 1
        max_reconnect_delay = 60

        while connection_id in self.active_connections:
            try:
                async with websockets.connect(url) as websocket:
                    logger.info(f"WebSocket connected: {connection_id}")
                    reconnect_delay = 1  # Reset delay on successful connection

                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Normalize based on stream type
                            if stream_type == "ticker":
                                normalized = self._normalize_ticker_data(data)
                            elif stream_type == "trade":
                                normalized = self._normalize_trade_data(data)
                            elif stream_type == "kline":
                                normalized = self._normalize_kline_data(data)
                            else:
                                normalized = data

                            # Call callback with normalized data
                            if asyncio.iscoroutinefunction(callback):
                                await callback(normalized)
                            else:
                                callback(normalized)

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse message: {e}")
                        except Exception as e:
                            logger.error(
                                f"Error processing message: {e}", exc_info=True
                            )

            except asyncio.CancelledError:
                logger.info(f"WebSocket task cancelled: {connection_id}")
                break
            except Exception as e:
                logger.error(
                    f"WebSocket error: {e}. Reconnecting in {reconnect_delay}s..."
                )
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


# TODO: Add error handling and retry logic
# TODO: Add rate limiting for REST API
# TODO: Add connection health monitoring
# TODO: Add automatic reconnection with exponential backoff
# TODO: Add data validation
