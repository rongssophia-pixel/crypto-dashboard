"""
Binance Connector
WebSocket and REST API client for Binance exchange
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
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
        # WebSocket URL - configurable to support different Binance regions
        # International: wss://stream.binance.com:9443
        # US: wss://stream.binance.us:9443
        websocket_url: str = "wss://stream.binance.us:9443",
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
        logger.info(f"BinanceConnector initialized with websocket_url: {websocket_url}")

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

    async def start_partial_book_stream(
        self,
        symbol: str,
        levels: int,
        speed_ms: int,
        callback: Callable[[Dict[str, Any]], None],
    ) -> str:
        """
        Start WebSocket stream for Binance partial orderbook (top N levels snapshot updates).

        Stream name format:
          - <symbol>@depth<levels>@<speed>ms
        Example:
          - btcusdt@depth20@100ms
        """
        connection_id = str(uuid.uuid4())

        symbol_lower = symbol.lower()
        url = f"{self.websocket_url}/ws/{symbol_lower}@depth{levels}@{speed_ms}ms"

        async def _orderbook_callback(raw: Dict[str, Any]):
            normalized = self._normalize_orderbook_data(
                raw, symbol_hint=symbol.upper(), levels=levels
            )
            if asyncio.iscoroutinefunction(callback):
                await callback(normalized)
            else:
                callback(normalized)

        task = asyncio.create_task(
            # Use passthrough and normalize with symbol_hint (partial book stream payload lacks symbol)
            self._websocket_handler(url, _orderbook_callback, connection_id, "passthrough")
        )
        self.active_connections[connection_id] = task

        logger.info(
            f"Started partial book stream for {symbol} (levels={levels}, speed_ms={speed_ms}): {connection_id}"
        )
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

    async def get_all_trading_symbols(
        self, quote_currency: str = "USDT"
    ) -> List[str]:
        """
        Fetch all trading symbols from exchange and filter by quote currency

        Args:
            quote_currency: Filter by quote currency (default: USDT)

        Returns:
            List of trading symbols (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        logger.info(f"Fetching all trading symbols with quote currency: {quote_currency}")
        
        try:
            exchange_info = await self.get_exchange_info()
            
            if not exchange_info or "symbols" not in exchange_info:
                logger.error("No symbols found in exchange info")
                return []
            
            # Filter symbols by quote currency and trading status
            symbols = []
            for symbol_info in exchange_info["symbols"]:
                # Check if symbol is trading and matches quote currency
                if (
                    symbol_info.get("status") == "TRADING"
                    and symbol_info.get("quoteAsset") == quote_currency
                ):
                    symbols.append(symbol_info["symbol"])
            
            logger.info(f"Found {len(symbols)} {quote_currency} trading pairs")
            return sorted(symbols)
            
        except Exception as e:
            logger.error(f"Error fetching trading symbols: {e}", exc_info=True)
            return []

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
            "type": "ticker",  # Add stream type
            "symbol": data.get("s"),
            "price": float(data.get("c", 0)),
            "volume": float(data.get("v", 0)),
            "bid_price": float(data.get("b", 0)),
            "ask_price": float(data.get("a", 0)),
            "bid_volume": float(data.get("B", 0)),
            "ask_volume": float(data.get("A", 0)),
            "open_24h": float(data.get("o", 0)),
            "high_24h": float(data.get("h", 0)),
            "low_24h": float(data.get("l", 0)),
            "volume_24h": float(data.get("v", 0)),
            "price_change_24h": float(data.get("p", 0)),
            "price_change_pct_24h": float(data.get("P", 0)),
            "trade_count": int(data.get("n", 0)),
            # Binance timestamps are milliseconds since epoch in UTC
            "timestamp": data.get(
                "E", int(datetime.now(timezone.utc).timestamp() * 1000)
            ),
            "exchange": "binance",
        }

    def _normalize_trade_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Binance trade data to standard format"""
        data = raw_data.get("data", {})

        return {
            "type": "trade",  # Add stream type
            "symbol": data.get("s"),
            "price": float(data.get("p", 0)),
            "volume": float(data.get("q", 0)),
            # Binance trade timestamps are milliseconds since epoch in UTC
            "timestamp": data.get(
                "T", int(datetime.now(timezone.utc).timestamp() * 1000)
            ),
            "trade_id": data.get("t"),
            "is_buyer_maker": data.get("m"),
            "exchange": "binance",
        }

    def _normalize_kline_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Binance kline data to standard format"""
        data = raw_data.get("data", {})
        kline = data.get("k", {})

        return {
            "type": "kline",  # Add stream type
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

    def _normalize_orderbook_data(
        self, raw_data: Dict[str, Any], *, symbol_hint: Optional[str] = None, levels: int = 20
    ) -> Dict[str, Any]:
        """
        Normalize Binance partial book depth stream data to canonical orderbook snapshot schema.

        Binance can deliver:
          - partial book: { lastUpdateId, bids, asks }
          - diff depth: { e, E, s, b, a, u, ... }
          - combined wrapper: { stream, data: {...} }
        We treat each message as a top-N snapshot suitable for UI replacement.
        """
        inner = raw_data.get("data", raw_data)

        # Determine symbol
        symbol = (
            symbol_hint
            or inner.get("s")
            or self._symbol_from_stream_name(raw_data.get("stream", ""))
        )

        # Extract levels (support multiple formats)
        bids_raw = inner.get("bids") or inner.get("b") or []
        asks_raw = inner.get("asks") or inner.get("a") or []

        def _parse_levels(side: list) -> list[list[float]]:
            out: list[list[float]] = []
            for lvl in side:
                if not isinstance(lvl, (list, tuple)) or len(lvl) < 2:
                    continue
                try:
                    price = float(lvl[0])
                    size = float(lvl[1])
                except Exception:
                    continue
                out.append([price, size])
            return out

        bids = _parse_levels(bids_raw)
        asks = _parse_levels(asks_raw)

        # Prefer event-time when present, otherwise fallback to now
        ts = inner.get("E") or inner.get("eventTime") or int(
            datetime.now(timezone.utc).timestamp() * 1000
        )

        # lastUpdateId for partial book; u for diff depth
        last_update_id = inner.get("lastUpdateId") or inner.get("u")

        return {
            "type": "orderbook",
            "symbol": symbol,
            "exchange": "binance",
            "timestamp": ts,
            "levels": levels,
            "bids": bids,
            "asks": asks,
            "last_update_id": last_update_id,
        }

    def _symbol_from_stream_name(self, stream_name: str) -> Optional[str]:
        """
        Parse symbol from combined stream name like 'btcusdt@depth20@100ms'.
        Returns uppercased symbol when possible.
        """
        if not stream_name or "@" not in stream_name:
            return None
        return stream_name.split("@", 1)[0].upper()

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
                logger.info(f"🔌 Attempting WebSocket connection to: {url}")
                # Binance requires ping/pong frames to keep connection alive
                async with websockets.connect(
                    url,
                    ping_interval=20,  # Send ping every 20 seconds
                    ping_timeout=20,   # Wait 20 seconds for pong response
                    close_timeout=10   # Timeout for close handshake
                ) as websocket:
                    logger.info(f"✅ WebSocket connected successfully: {connection_id}")
                    reconnect_delay = 1  # Reset delay on successful connection

                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            
                            # Log first few messages for debugging
                            if not hasattr(self, '_message_count'):
                                self._message_count = {}
                            if connection_id not in self._message_count:
                                self._message_count[connection_id] = 0
                            
                            self._message_count[connection_id] += 1
                            if self._message_count[connection_id] <= 3:
                                logger.info(f"WebSocket message #{self._message_count[connection_id]} received: {json.dumps(data)[:200]}")

                            # Normalize based on stream type
                            if stream_type == "ticker":
                                normalized = self._normalize_ticker_data(data)
                            elif stream_type == "trade":
                                normalized = self._normalize_trade_data(data)
                            elif stream_type == "kline":
                                normalized = self._normalize_kline_data(data)
                            elif stream_type == "orderbook":
                                # Keep orderbook normalization lightweight; symbol may be provided by stream wrapper
                                normalized = self._normalize_orderbook_data(data)
                            elif stream_type == "combined":
                                # For combined streams, pass raw data to callback
                                # Callback will route based on stream name
                                normalized = data
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

    async def start_all_streams(
        self,
        symbols: List[str],
        intervals: List[str],
        kline_callback: Callable[[Dict[str, Any]], None],
        ticker_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        max_symbols_per_connection: int = 50,
    ) -> List[str]:
        """
        Start kline and ticker streams for all symbols with connection pooling

        Args:
            symbols: List of trading symbols
            intervals: List of kline intervals (e.g., ['1m', '5m', '1h'])
            kline_callback: Callback for kline data
            ticker_callback: Optional callback for ticker data
            max_symbols_per_connection: Max symbols per WebSocket connection

        Returns:
            List of connection IDs
        """
        logger.info(
            f"Starting streams for {len(symbols)} symbols, "
            f"{len(intervals)} intervals, ticker={'enabled' if ticker_callback else 'disabled'}"
        )

        connection_ids = []
        
        # Calculate streams per symbol
        streams_per_symbol = len(intervals) + (1 if ticker_callback else 0)
        logger.info(f"Streams per symbol: {streams_per_symbol}")
        
        # Split symbols into batches to avoid hitting 1024 stream limit
        symbols_per_batch = max_symbols_per_connection
        batches = [
            symbols[i : i + symbols_per_batch]
            for i in range(0, len(symbols), symbols_per_batch)
        ]
        
        logger.info(
            f"Creating {len(batches)} WebSocket connections "
            f"({symbols_per_batch} symbols per connection)"
        )

        # Create a connection for each batch
        for batch_idx, symbol_batch in enumerate(batches):
            try:
                connection_id = await self._start_combined_stream(
                    symbols=symbol_batch,
                    intervals=intervals,
                    kline_callback=kline_callback,
                    ticker_callback=ticker_callback,
                    connection_name=f"batch-{batch_idx}",
                )
                connection_ids.append(connection_id)
                logger.info(
                    f"✅ Started connection {batch_idx + 1}/{len(batches)}: "
                    f"{len(symbol_batch)} symbols, {len(symbol_batch) * streams_per_symbol} streams"
                )
            except Exception as e:
                logger.error(
                    f"Failed to start connection for batch {batch_idx}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"✅ All streams started: {len(connection_ids)} connections, "
            f"{len(symbols)} symbols, ~{len(symbols) * streams_per_symbol} total streams"
        )
        return connection_ids

    async def _start_combined_stream(
        self,
        symbols: List[str],
        intervals: List[str],
        kline_callback: Callable[[Dict[str, Any]], None],
        ticker_callback: Optional[Callable[[Dict[str, Any]], None]],
        connection_name: str,
    ) -> str:
        """
        Start a combined WebSocket stream with multiple symbols and stream types

        Args:
            symbols: List of symbols for this connection
            intervals: Kline intervals
            kline_callback: Callback for kline data
            ticker_callback: Callback for ticker data
            connection_name: Name for this connection

        Returns:
            Connection ID
        """
        connection_id = f"{connection_name}-{uuid.uuid4()}"
        
        # Build stream list
        streams = []
        
        # Add kline streams for each symbol and interval
        for symbol in symbols:
            symbol_lower = symbol.lower()
            for interval in intervals:
                streams.append(f"{symbol_lower}@kline_{interval}")
        
        # Add ticker streams if enabled
        if ticker_callback:
            for symbol in symbols:
                symbol_lower = symbol.lower()
                streams.append(f"{symbol_lower}@ticker")
        
        # Build combined stream URL
        stream_names = "/".join(streams)
        url = f"{self.websocket_url}/stream?streams={stream_names}"
        
        # Check URL length to avoid HTTP 414 errors
        url_length = len(url)
        logger.info(
            f"Starting combined stream: {connection_name} with {len(streams)} streams "
            f"(URL length: {url_length} chars)"
        )
        
        if url_length > 8000:
            logger.warning(
                f"⚠️  URL length ({url_length}) is very long and may cause HTTP 414 errors. "
                f"Consider reducing max_symbols_per_connection (current: {len(symbols)} symbols)"
            )
        
        # Create callback router to dispatch to correct handler
        async def combined_callback(data):
            stream = data.get("stream", "")
            if "@kline_" in stream:
                if asyncio.iscoroutinefunction(kline_callback):
                    await kline_callback(data)
                else:
                    kline_callback(data)
            elif "@ticker" in stream and ticker_callback:
                if asyncio.iscoroutinefunction(ticker_callback):
                    await ticker_callback(data)
                else:
                    ticker_callback(data)
        
        # Start WebSocket handler
        task = asyncio.create_task(
            self._websocket_handler(
                url, combined_callback, connection_id, "combined"
            )
        )
        self.active_connections[connection_id] = task
        
        return connection_id

    async def close(self):
        """
        Close all active WebSocket connections
        
        Cancels all active connection tasks and cleans up resources.
        """
        logger.info(f"Closing BinanceConnector with {len(self.active_connections)} active connections...")
        
        # Get list of connection IDs to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        
        # Stop all active streams
        for connection_id in connection_ids:
            try:
                await self.stop_stream(connection_id)
            except Exception as e:
                logger.error(f"Error stopping stream {connection_id}: {e}")
        
        logger.info("BinanceConnector closed")


# TODO: Add error handling and retry logic
# TODO: Add rate limiting for REST API
# TODO: Add connection health monitoring
# TODO: Add automatic reconnection with exponential backoff
# TODO: Add data validation
