import logging
import grpc
from datetime import datetime, timezone
from typing import AsyncGenerator

from proto import analytics_pb2, analytics_pb2_grpc, common_pb2
from services.analytics_service import AnalyticsBusinessService

logger = logging.getLogger(__name__)

def dt_to_timestamp(dt: datetime) -> common_pb2.Timestamp:
    """Convert datetime to common.Timestamp"""
    if not dt:
        return common_pb2.Timestamp()
    
    # Treat naive datetimes as UTC and normalize aware datetimes to UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    
    ts = common_pb2.Timestamp()
    ts.seconds = int(dt.timestamp())
    ts.nanos = int(dt.microsecond * 1000)
    return ts

def timestamp_to_dt(ts: common_pb2.Timestamp) -> datetime:
    """Convert common.Timestamp to datetime"""
    if not ts or (ts.seconds == 0 and ts.nanos == 0):
        # Default to now if not provided, or handle as None depending on usage
        # But for start_time/end_time usually we need values.
        # However, the proto uses message which is nullable/optional.
        return None
        
    return datetime.fromtimestamp(ts.seconds + ts.nanos / 1e9, tz=timezone.utc)

class AnalyticsServiceServicer(analytics_pb2_grpc.AnalyticsServiceServicer):
    """
    gRPC Servicer for Analytics Service
    Real-time query engine for market data
    """

    def __init__(self, analytics_service: AnalyticsBusinessService):
        self.analytics_service = analytics_service

    async def QueryMarketData(self, request, context):
        """Query raw market data points"""
        try:
            start_time = timestamp_to_dt(request.start_time)
            end_time = timestamp_to_dt(request.end_time)
            
            # If timestamps are missing, we might need defaults, but business service validates range.
            # Let's assume client sends valid timestamps or business service raises ValueError.
            if not start_time or not end_time:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "start_time and end_time are required")

            result = await self.analytics_service.query_market_data(
                symbols=list(request.symbols),
                start_time=start_time,
                end_time=end_time,
                limit=request.limit,
                offset=request.offset,
                order_by=request.order_by
            )

            response = analytics_pb2.QueryResponse(
                total_count=result.get('total_count', 0),
                has_more=result.get('has_more', False)
            )
            
            for item in result.get('data', []):
                point = analytics_pb2.MarketDataPoint(
                    symbol=item['symbol'],
                    timestamp=dt_to_timestamp(item['timestamp']),
                    price=item['price'],
                    volume=item['volume'],
                    bid_price=item['bid_price'],
                    ask_price=item['ask_price']
                )
                
                # Add metrics map
                if 'metrics' in item:
                    for k, v in item['metrics'].items():
                        point.metrics[k] = v
                
                response.data.append(point)

            return response
            
        except ValueError as e:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except Exception as e:
            logger.error(f"Error in QueryMarketData: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def GetCandles(self, request, context):
        """Get aggregated candles (OHLCV)"""
        try:
            start_time = timestamp_to_dt(request.start_time)
            end_time = timestamp_to_dt(request.end_time)
            
            if not start_time or not end_time:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "start_time and end_time are required")

            result = await self.analytics_service.get_candles(
                symbol=request.symbol,
                interval=request.interval,
                start_time=start_time,
                end_time=end_time,
                limit=request.limit
            )

            response = analytics_pb2.CandleResponse(
                total_count=result.get('total_count', 0)
            )
            
            for item in result.get('candles', []):
                candle = analytics_pb2.Candle(
                    timestamp=dt_to_timestamp(item['timestamp']),
                    open=item['open'],
                    high=item['high'],
                    low=item['low'],
                    close=item['close'],
                    volume=item['volume'],
                    trade_count=item['trade_count']
                )
                response.candles.append(candle)

            return response

        except ValueError as e:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except Exception as e:
            logger.error(f"Error in GetCandles: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def GetAggregatedMetrics(self, request, context):
        """Get calculated metrics (volatility, averages, etc.)"""
        try:
            start_time = timestamp_to_dt(request.start_time)
            end_time = timestamp_to_dt(request.end_time)
            
            if not start_time or not end_time:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "start_time and end_time are required")

            result = await self.analytics_service.get_aggregated_metrics(
                symbol=request.symbol,
                metric_types=list(request.metric_types),
                start_time=start_time,
                end_time=end_time,
                time_bucket=request.time_bucket
            )

            response = analytics_pb2.AggregationResponse(
                symbol=result.get('symbol', request.symbol)
            )
            
            # Map overall metrics
            for k, v in result.get('metrics', {}).items():
                response.metrics[k] = v
                
            # Map time series
            for item in result.get('time_series', []):
                ts_point = analytics_pb2.TimeSeriesPoint(
                    timestamp=dt_to_timestamp(item['timestamp'])
                )
                for k, v in item['values'].items():
                    ts_point.values[k] = v
                
                response.time_series.append(ts_point)

            return response

        except ValueError as e:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except Exception as e:
            logger.error(f"Error in GetAggregatedMetrics: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def StreamRealTimeData(self, request, context):
        """Stream real-time market data"""
        # TODO: Implement streaming logic
        await context.abort(grpc.StatusCode.UNIMPLEMENTED, "Streaming not yet implemented")
