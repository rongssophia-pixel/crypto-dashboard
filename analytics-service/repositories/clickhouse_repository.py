"""
ClickHouse Repository
Handles ClickHouse database operations for analytics
"""

import asyncio
import logging
import math
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from clickhouse_driver import Client

logger = logging.getLogger(__name__)


def sanitize_float(value: Any) -> float:
    """
    Sanitize float values to handle NaN and Inf

    Args:
        value: Value to sanitize

    Returns:
        Sanitized float value (NaN/Inf converted to 0.0)
    """
    if value is None:
        return 0.0

    try:
        float_value = float(value)
        if math.isnan(float_value) or math.isinf(float_value):
            return 0.0
        return float_value
    except (ValueError, TypeError):
        return 0.0


# Valid candle intervals
VALID_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}

# Time bucket mappings for aggregations
TIME_BUCKET_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}


class ClickHouseRepository:
    """
    Repository for ClickHouse operations
    Handles all time-series data queries
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str = "default",
        password: str = "",
        secure: bool = False,
        verify: bool = True,
    ):
        """
        Initialize repository with ClickHouse connection parameters

        Args:
            host: ClickHouse host
            port: ClickHouse port
            database: Database name
            user: Username
            password: Password
            secure: Use TLS/SSL
            verify: Verify SSL certificate
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.secure = secure
        self.verify = verify
        self.client: Optional[Client] = None

        logger.info(f"ClickHouseRepository initialized for {host}:{port}/{database}")

    async def connect(self) -> None:
        """Establish connection to ClickHouse"""
        logger.info(f"Connecting to ClickHouse at {self.host}:{self.port}...")

        self.client = Client(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            secure=self.secure,
            verify=self.verify,
        )

        # Test connection
        result = self.client.execute("SELECT 1")
        logger.info(f"✅ ClickHouse connection established: {result}")

    async def disconnect(self) -> None:
        """Close ClickHouse connection"""
        if self.client:
            self.client.disconnect()
            logger.info("ClickHouse connection closed")

    async def query_market_data(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        limit: int,
        offset: int,
        order_by: str = "timestamp_desc",
    ) -> Dict[str, Any]:
        """
        Query raw market data from ClickHouse

        Args:
            symbols: List of symbols to query
            start_time: Start timestamp
            end_time: End timestamp
            limit: Maximum records
            offset: Pagination offset
            order_by: Sort order (timestamp_asc or timestamp_desc)

        Returns:
            Dict with data and pagination info
        """
        if not self.client:
            raise RuntimeError("ClickHouse client not connected")

        # Determine sort order
        sort_order = "DESC" if order_by == "timestamp_desc" else "ASC"

        # Build query
        query = f"""
            SELECT
                symbol,
                timestamp,
                price,
                volume,
                bid_price,
                ask_price,
                high_24h,
                low_24h,
                volume_24h,
                price_change_24h,
                price_change_pct_24h,
                trade_count
            FROM market_data
            WHERE symbol IN %(symbols)s
                AND timestamp >= %(start_time)s
                AND timestamp <= %(end_time)s
            ORDER BY timestamp {sort_order}
            LIMIT %(limit)s
            OFFSET %(offset)s
        """

        # Get total count for pagination
        count_query = """
            SELECT count(*) as cnt
            FROM market_data
            WHERE symbol IN %(symbols)s
                AND timestamp >= %(start_time)s
                AND timestamp <= %(end_time)s
        """

        params = {
            "symbols": symbols,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
            "offset": offset,
        }

        try:
            # Execute data query
            rows = self.client.execute(query, params)
            logger.info("printing result")
            logger.info(rows)
            # Execute count query
            count_result = self.client.execute(count_query, params)
            total_count = count_result[0][0] if count_result else 0

            # Transform results
            data = []
            for row in rows:
                data.append(
                    {
                        "symbol": row[0],
                        "timestamp": row[1],
                        "price": sanitize_float(row[2]),
                        "volume": sanitize_float(row[3]),
                        "bid_price": sanitize_float(row[4]),
                        "ask_price": sanitize_float(row[5]),
                        "metrics": {
                            "high_24h": sanitize_float(row[6]),
                            "low_24h": sanitize_float(row[7]),
                            "volume_24h": sanitize_float(row[8]),
                            "price_change_24h": sanitize_float(row[9]),
                            "price_change_pct_24h": sanitize_float(row[10]),
                        },
                        "trade_count": int(row[11]),
                    }
                )

            return {
                "data": data,
                "total_count": total_count,
                "has_more": (offset + len(data)) < total_count,
            }

        except Exception as e:
            logger.error(f"Error querying market data: {e}", exc_info=True)
            raise

    async def query_candles(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> Dict[str, Any]:
        """
        Query aggregated candles

        Args:
            symbol: Trading symbol
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            start_time: Start timestamp
            end_time: End timestamp
            limit: Maximum candles

        Returns:
            Dict with candles and count
        """
        if not self.client:
            raise RuntimeError("ClickHouse client not connected")

        # Validate interval
        if interval not in VALID_INTERVALS:
            raise ValueError(
                f"Invalid interval: {interval}. Must be one of {VALID_INTERVALS}"
            )

        query = """
            SELECT
                timestamp,
                open,
                high,
                low,
                close,
                volume,
                trade_count
            FROM market_candles
            WHERE symbol = %(symbol)s
                AND interval = %(interval)s
                AND timestamp >= %(start_time)s
                AND timestamp <= %(end_time)s
            ORDER BY timestamp DESC
            LIMIT %(limit)s
        """

        params = {
            "symbol": symbol,
            "interval": interval,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }

        try:
            rows = self.client.execute(query, params)

            candles = []
            for row in rows:
                candles.append(
                    {
                        "timestamp": row[0],
                        "open": sanitize_float(row[1]),
                        "high": sanitize_float(row[2]),
                        "low": sanitize_float(row[3]),
                        "close": sanitize_float(row[4]),
                        "volume": sanitize_float(row[5]),
                        "trade_count": int(row[6]),
                    }
                )

            return {
                "candles": candles,
                "total_count": len(candles),
            }

        except Exception as e:
            logger.error(f"Error querying candles: {e}", exc_info=True)
            raise

    async def calculate_aggregates(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        metric_types: List[str],
        time_bucket: str = "1h",
    ) -> Dict[str, Any]:
        """
        Calculate aggregate metrics

        Args:
            symbol: Trading symbol
            start_time: Start timestamp
            end_time: End timestamp
            metric_types: List of metrics to calculate
            time_bucket: Time bucket for time series (1h, 1d, 1w)

        Returns:
            Dictionary of metric values and time series
        """
        if not self.client:
            raise RuntimeError("ClickHouse client not connected")

        # Build metric selections
        metric_selectors = []
        available_metrics = {
            "avg_price": "avg(price)",
            "total_volume": "sum(volume)",
            "volatility": "stddevPop(price)",
            "min_price": "min(price)",
            "max_price": "max(price)",
            "vwap": "sum(price * volume) / nullIf(sum(volume), 0)",
            "trade_count": "sum(trade_count)",
            "price_range": "max(price) - min(price)",
            "price_range_pct": "(max(price) - min(price)) / nullIf(min(price), 0) * 100",
        }

        for metric in metric_types:
            if metric in available_metrics:
                metric_selectors.append(f"{available_metrics[metric]} as {metric}")

        if not metric_selectors:
            metric_selectors = [f"{available_metrics['avg_price']} as avg_price"]

        # Overall aggregation query
        overall_query = f"""
            SELECT
                {', '.join(metric_selectors)}
            FROM market_data
            WHERE symbol = %(symbol)s
                AND timestamp >= %(start_time)s
                AND timestamp <= %(end_time)s
        """

        # Time series aggregation query
        bucket_seconds = TIME_BUCKET_SECONDS.get(time_bucket, 3600)
        time_series_query = f"""
            SELECT
                toStartOfInterval(timestamp, INTERVAL {bucket_seconds} second) as bucket,
                {', '.join(metric_selectors)}
            FROM market_data
            WHERE symbol = %(symbol)s
                AND timestamp >= %(start_time)s
                AND timestamp <= %(end_time)s
            GROUP BY bucket
            ORDER BY bucket ASC
        """

        params = {
            "symbol": symbol,
            "start_time": start_time,
            "end_time": end_time,
        }

        try:
            # Get overall metrics
            overall_result = self.client.execute(overall_query, params)

            metrics = {}
            if overall_result and overall_result[0]:
                for i, metric in enumerate(metric_types):
                    if metric in available_metrics and i < len(overall_result[0]):
                        value = overall_result[0][i]
                        metrics[metric] = sanitize_float(value)

            # Get time series
            time_series_result = self.client.execute(time_series_query, params)

            time_series = []
            for row in time_series_result:
                point = {"timestamp": row[0], "values": {}}
                for i, metric in enumerate(metric_types):
                    if metric in available_metrics and (i + 1) < len(row):
                        value = row[i + 1]
                        point["values"][metric] = sanitize_float(value)
                time_series.append(point)

            # Calculate price change if requested
            if "price_change_pct" in metric_types and len(time_series) >= 2:
                first_price = time_series[0]["values"].get("avg_price", 0)
                last_price = time_series[-1]["values"].get("avg_price", 0)
                if first_price > 0:
                    price_change = ((last_price - first_price) / first_price) * 100
                    metrics["price_change_pct"] = sanitize_float(price_change)

            return {
                "symbol": symbol,
                "metrics": metrics,
                "time_series": time_series,
            }

        except Exception as e:
            logger.error(f"Error calculating aggregates: {e}", exc_info=True)
            raise

    async def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest price and stats for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Latest price data with 24h stats or None
        """
        if not self.client:
            raise RuntimeError("ClickHouse client not connected")

        query = """
            SELECT
                symbol,
                timestamp,
                price,
                volume,
                bid_price,
                ask_price,
                high_24h,
                low_24h,
                volume_24h,
                price_change_24h,
                price_change_pct_24h,
                trade_count
            FROM market_data
            WHERE symbol = %(symbol)s
            ORDER BY timestamp DESC
            LIMIT 1
        """

        params = {
            "symbol": symbol,
        }

        try:
            rows = self.client.execute(query, params)

            if rows:
                row = rows[0]
                return {
                    "symbol": row[0],
                    "timestamp": row[1],
                    "price": sanitize_float(row[2]),
                    "volume": sanitize_float(row[3]),
                    "bid_price": sanitize_float(row[4]),
                    "ask_price": sanitize_float(row[5]),
                    "high_24h": sanitize_float(row[6]),
                    "low_24h": sanitize_float(row[7]),
                    "volume_24h": sanitize_float(row[8]),
                    "price_change_24h": sanitize_float(row[9]),
                    "price_change_pct_24h": sanitize_float(row[10]),
                    "trade_count": int(row[11]),
                }
            return None

        except Exception as e:
            logger.error(f"Error getting latest price: {e}", exc_info=True)
            raise

    async def get_latest_prices_batch(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Get latest prices for multiple symbols

        Args:
            symbols: List of trading symbols

        Returns:
            List of latest price data
        """
        if not self.client:
            raise RuntimeError("ClickHouse client not connected")

        # Use ORDER BY timestamp DESC and LIMIT BY symbol to get latest record per symbol
        # This avoids the nested aggregate function issue
        query = """
            SELECT
                symbol,
                timestamp,
                price,
                volume,
                bid_price,
                ask_price,
                volume_24h,
                price_change_pct_24h
            FROM market_data
            WHERE symbol IN %(symbols)s
            ORDER BY timestamp DESC
            LIMIT 1 BY symbol
        """

        params = {
            "symbols": symbols,
        }

        try:
            rows = self.client.execute(query, params)

            results = []
            for row in rows:
                results.append(
                    {
                        "symbol": row[0],
                        "timestamp": row[1],
                        "price": sanitize_float(row[2]),
                        "volume": sanitize_float(row[3]),
                        "bid_price": sanitize_float(row[4]),
                        "ask_price": sanitize_float(row[5]),
                        "volume_24h": sanitize_float(row[6]),
                        "change_24h": sanitize_float(row[7]),  # Percentage change for Latest Prices
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error getting latest prices batch: {e}", exc_info=True)
            raise

    async def export_data_range(
        self,
        data_type: str,
        start_time: datetime,
        end_time: datetime,
        symbols: Optional[List[str]] = None,
        batch_size: int = 100000,
    ) -> AsyncIterator[List[Dict[str, Any]]]:
        """
        Stream ClickHouse data in batches for archival to cold storage.

        Args:
            data_type: Table to export (market_data, market_candles, alert_events)
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            symbols: Optional symbol filter
            batch_size: Number of rows per batch

        Yields:
            Batches of rows as list[dict]
        """
        if not self.client:
            raise RuntimeError("ClickHouse client not connected")

        table_map = {
            "market_data": {
                "table": "market_data",
                "columns": [
                    "timestamp",
                    "symbol",
                    "exchange",
                    "price",
                    "volume",
                    "bid_price",
                    "ask_price",
                    "bid_volume",
                    "ask_volume",
                    "high_24h",
                    "low_24h",
                    "volume_24h",
                    "price_change_24h",
                    "price_change_pct_24h",
                    "trade_count",
                    "metadata",
                ],
            },
            "market_candles": {
                "table": "market_candles",
                "columns": [
                    "timestamp",
                    "symbol",
                    "exchange",
                    "interval",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "quote_volume",
                    "trade_count",
                    "taker_buy_volume",
                    "taker_buy_quote_volume",
                ],
            },
            "alert_events": {
                "table": "alert_events",
                "columns": [
                    "timestamp",
                    "alert_id",
                    "user_id",
                    "symbol",
                    "condition_type",
                    "threshold_value",
                    "triggered_value",
                    "comparison_operator",
                    "message",
                    "metadata",
                ],
            },
        }

        if data_type not in table_map:
            raise ValueError(f"Unsupported data_type: {data_type}")

        table_info = table_map[data_type]
        columns = table_info["columns"]

        where_clauses = [
            "timestamp >= %(start_time)s",
            "timestamp <= %(end_time)s",
        ]
        params: Dict[str, Any] = {
            "start_time": start_time,
            "end_time": end_time,
            "limit": batch_size,
            "offset": 0,
        }
        if symbols:
            where_clauses.append("symbol IN %(symbols)s")
            params["symbols"] = symbols

        query = f"""
            SELECT {", ".join(columns)}
            FROM {table_info["table"]}
            WHERE {" AND ".join(where_clauses)}
            ORDER BY timestamp ASC
            LIMIT %(limit)s
            OFFSET %(offset)s
        """

        offset = 0
        try:
            while True:
                params["offset"] = offset
                rows = await asyncio.to_thread(self.client.execute, query, params)

                if not rows:
                    break

                batch = [
                    {col: row[idx] for idx, col in enumerate(columns)} for row in rows
                ]
                yield batch

                if len(rows) < batch_size:
                    break

                offset += batch_size
        except Exception as e:
            logger.error(
                "Error exporting data_type=%s range %s - %s: %s",
                data_type,
                start_time,
                end_time,
                e,
                exc_info=True,
            )
            raise

    async def delete_data_before(
        self,
        data_type: str,
        cutoff_time: datetime,
        symbols: Optional[List[str]] = None,
    ) -> int:
        """
        Delete data older than cutoff_time from ClickHouse.
        Used after successful archival to cold storage.

        Args:
            data_type: Table to delete from (market_data, market_candles, alert_events)
            cutoff_time: Delete data with timestamp before this time
            symbols: Optional symbol filter (delete only specific symbols)

        Returns:
            Number of rows deleted (approximate, ClickHouse returns affected parts)
        """
        if not self.client:
            raise RuntimeError("ClickHouse client not connected")

        table_map = {
            "market_data": "market_data",
            "market_candles": "market_candles",
            "alert_events": "alert_events",
        }

        if data_type not in table_map:
            raise ValueError(f"Unsupported data_type: {data_type}")

        table = table_map[data_type]

        where_clauses = ["timestamp < %(cutoff_time)s"]
        params: Dict[str, Any] = {"cutoff_time": cutoff_time}

        if symbols:
            where_clauses.append("symbol IN %(symbols)s")
            params["symbols"] = symbols

        # First, get count of rows to be deleted (for logging/return)
        count_query = f"""
            SELECT count() as cnt
            FROM {table}
            WHERE {" AND ".join(where_clauses)}
        """

        try:
            count_result = await asyncio.to_thread(
                self.client.execute, count_query, params
            )
            rows_to_delete = count_result[0][0] if count_result else 0

            if rows_to_delete == 0:
                logger.info(
                    "No data to delete for %s before %s", data_type, cutoff_time
                )
                return 0

            # Execute delete using ALTER TABLE DELETE (lightweight delete)
            delete_query = f"""
                ALTER TABLE {table}
                DELETE WHERE {" AND ".join(where_clauses)}
            """

            await asyncio.to_thread(self.client.execute, delete_query, params)

            logger.info(
                "Deleted %d rows from %s before %s",
                rows_to_delete,
                data_type,
                cutoff_time,
            )
            return rows_to_delete

        except Exception as e:
            logger.error(
                "Error deleting data_type=%s before %s: %s",
                data_type,
                cutoff_time,
                e,
                exc_info=True,
            )
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        return {
            "connected": self.client is not None,
            "host": self.host,
            "port": self.port,
            "database": self.database,
        }
