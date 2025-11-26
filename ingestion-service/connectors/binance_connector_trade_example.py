import asyncio
import json
import logging
from typing import Any, Callable, Dict

import websockets

# --- Configuration ---
BINANCE_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"
STREAM_TYPE = "trade"  # Valid types: "ticker", "trade", "kline", etc.
CONNECTION_ID = "BTCUSDT_TradeStream"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BinanceConnector:
    """
    Manages WebSocket connections with robust auto-reconnection and data handling.
    """

    def __init__(self):
        # Dictionary to track active connections and their state.
        # Key: connection_id, Value: asyncio.Task
        self.active_connections: Dict[str, asyncio.Task] = {}
        # Used as a simple callback for testing.
        self.callback: Callable[[Any], None] = self._default_callback

    def _default_callback(self, data: Any):
        """A simple function to receive and print the normalized data."""
        # Print only the essential trade data to keep the console clean
        if isinstance(data, dict) and data.get("stream_type") == "trade":
            print(
                f"✅ Trade Data | Symbol: {data.get('symbol', 'N/A')} | Price: {data.get('price', 'N/A')} | Qty: {data.get('quantity', 'N/A')}"
            )
        else:
            print(f"✅ Normalized Data: {data}")

    def _normalize_trade_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mocks the normalization step for a Binance Trade stream.
        In a real application, this transforms the cryptic fields (e.g., 'p', 'q')
        into readable names (e.g., 'price', 'quantity').
        """
        # Example of raw Binance trade data format:
        # {"e":"trade","E":1672531200000,"s":"BTCUSDT","p":"20000.00","q":"0.1"}

        return {
            "stream_type": "trade",
            "event_time": raw_data.get("E"),
            "symbol": raw_data.get("s"),
            "price": float(raw_data.get("p", 0.0)),
            "quantity": float(raw_data.get("q", 0.0)),
            "trade_id": raw_data.get("t"),
        }

    # --- THE CORE HANDLER METHOD ---
    async def _websocket_handler(
        self, url: str, stream_type: str, connection_id: str, callback: Callable
    ):
        """
        Connects to a WebSocket URL and handles reconnection with exponential backoff.
        """

        # Exponential backoff parameters
        reconnect_delay = 1
        max_reconnect_delay = 60

        # Outer loop ensures continuous reconnection attempts
        while connection_id in self.active_connections:
            try:
                # 1. websockets is now imported and correctly used
                # Added a timeout to prevent connection attempts from blocking indefinitely
                async with websockets.connect(url, open_timeout=10) as websocket:
                    logger.info(f"WebSocket connected: {connection_id}")
                    reconnect_delay = 1  # Reset delay on successful connection

                    # --- CRITICAL: Initial Subscription/Setup ---
                    # For combined streams (e.g., /stream?streams=), you must send a
                    # subscription message here. For single streams (e.g., /ws/symbol@stream),
                    # the connection often implies subscription, but it's good practice
                    # to confirm or send a ping.

                    # Since we are using the simple single stream, we skip an explicit
                    # subscription message, but we are ready for messages.

                    # Inner loop processes incoming messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Normalization based on stream type (resolves the 'stream_type' error)
                            if stream_type == "ticker":
                                # Assuming self._normalize_ticker_data exists
                                normalized = data  # Use raw data as fallback
                            elif stream_type == "trade":
                                normalized = self._normalize_trade_data(data)
                            elif stream_type == "kline":
                                # Assuming self._normalize_kline_data exists
                                normalized = data  # Use raw data as fallback
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
                # Catches graceful shutdown signal
                logger.info(f"WebSocket task cancelled: {connection_id}")
                break  # Exit the while loop
            except Exception as e:
                # Catches connection errors (timeouts, refused, disconnects, etc.)
                logger.error(
                    f"WebSocket error: {e.__class__.__name__} - {e}. Reconnecting in {reconnect_delay}s..."
                )
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(
                    reconnect_delay * 2, max_reconnect_delay
                )  # Exponential backoff

    def start_stream(
        self, url: str, stream_type: str, connection_id: str, callback: Callable
    ):
        """Starts the WebSocket handler as an asyncio task."""
        if connection_id in self.active_connections:
            logger.warning(f"Connection {connection_id} already active.")
            return

        logger.info(f"Starting connection task: {connection_id}")
        task = asyncio.create_task(
            self._websocket_handler(url, stream_type, connection_id, callback)
        )
        self.active_connections[connection_id] = task

    async def stop_stream(self, connection_id: str):
        """Gracefully stops a running WebSocket stream task."""
        if connection_id in self.active_connections:
            task = self.active_connections.pop(connection_id)
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            logger.info(f"Connection {connection_id} stopped.")


async def main():
    """Main function to test the connector."""
    connector = BinanceConnector()

    # Start the stream
    connector.start_stream(BINANCE_URL, STREAM_TYPE, CONNECTION_ID, connector.callback)

    # Let the stream run for 30 seconds for observation
    logger.info("Running for 30 seconds. Press Ctrl+C to stop sooner.")
    await asyncio.sleep(30)

    # Gracefully stop the stream
    await connector.stop_stream(CONNECTION_ID)
    logger.info("Application finished cleanly.")


if __name__ == "__main__":
    try:
        # Start the asyncio event loop and run the main function
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program manually interrupted by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

# ... (your existing imports)

# Assume your handler function is accessible here:
# async def _websocket_handler(url, stream_type, callback):
#     ... (the code you provided)


async def main_test_run():
    """Sets up and runs the handler."""

    # 1. Define URL and stream type
    BINANCE_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"  # noqa: F841
    STREAM_TYPE = "trade"  # noqa: F841

    # 2. To avoid the unresolved reference errors in the handler,
    # we'll mock the required class context if the handler is a method.
    # If the handler is a standalone function, you can call it directly.

    # *** IMPORTANT ***
    # Replace the call below with the actual way you call your handler.
    # Example for calling a standalone async function:
    # await _websocket_handler(BINANCE_URL, STREAM_TYPE, simple_callback)

    # Example for calling a class method (like your provided code suggests):
    # This requires defining a class instance and managing 'active_connections'
    # and 'connection_id'.

    # For a simple run, let's just make sure the handler runs for 30 seconds
    # using a mock connection management structure.

    # --- Start of Mock Run ---
    print("Starting WebSocket handler...")

    # In a real setup, this task would be created by your main application logic
    # task = asyncio.create_task(
    #     your_connector._websocket_handler(BINANCE_URL, STREAM_TYPE, simple_callback)
    # )

    # In your environment, execute the line that calls your handler.
    # For this demonstration, we'll simulate the execution:

    # Run for 30 seconds
    await asyncio.sleep(30)

    # In a real app, you would now cancel the task (e.g., task.cancel())
    print("Test finished after 30 seconds.")
    # --- End of Mock Run ---


if __name__ == "__main__":
    try:
        # This starts the asynchronous event loop
        asyncio.run(main_test_run())
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
