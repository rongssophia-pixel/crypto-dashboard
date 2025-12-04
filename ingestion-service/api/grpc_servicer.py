"""
Ingestion Service gRPC Servicer
Implements the IngestionService gRPC interface
"""

import logging
from concurrent import futures

import grpc

from proto import common_pb2, ingestion_pb2, ingestion_pb2_grpc  # noqa: F401

from services.ingestion_service import IngestionBusinessService

logger = logging.getLogger(__name__)


class IngestionServiceServicer:
    """
    gRPC servicer for Ingestion Service
    Implements ingestion_pb2_grpc.IngestionServiceServicer
    """

    def __init__(self, business_service, kafka_topic_raw):
        """
        Initialize servicer with business service

        Args:
            business_service: IngestionBusinessService instance
        """
        self.business_service = business_service
        self.kafka_topic_raw = kafka_topic_raw
        logger.info("IngestionServiceServicer initialized")

    async def StartDataStream(self, request, context):
        """
        Start streaming market data for given symbols

        Args:
            request: StartStreamRequest from proto
            context: gRPC context

        Returns:
            StartStreamResponse
        """
        # TODO: Implement StartDataStream
        # 1. Validate tenant context
        # 2. Call business service to start stream
        # 3. Return response with stream_id
        try:
            # Extract tenant context
            tenant_id = request.context.tenant_id
            user_id = request.context.user_id

            logger.info(f"StartDataStream request from tenant {tenant_id} for {request.symbols}")

            # Start stream via business service
            result = await self.business_service.start_stream(
                tenant_id=tenant_id,
                symbols=list(request.symbols),
                exchange=request.exchange,
                stream_type=request.stream_type,
                kafka_topic=self.kafka_topic_raw
            )

            # Build response
            return ingestion_pb2.StartStreamResponse(
                stream_id=result["stream_id"],
                success=True,
                message="Stream started successfully",
                started_at=common_pb2.Timestamp(
                    seconds=int(result["started_at"].timestamp()) if hasattr(result["started_at"], 'timestamp') else 0
                )
            )

        except Exception as e:
            logger.error(f"StartDataStream error: {e}", exc_info=True)
            return ingestion_pb2.StartStreamResponse(
                stream_id="",
                success=False,
                message=f"Error: {str(e)}"
            )

    async def StopDataStream(self, request, context):
        """
        Stop an active data stream

        Args:
            request: StopStreamRequest from proto
            context: gRPC context

        Returns:
            Empty
        """
        # TODO: Implement StopDataStream
        # 1. Validate stream ownership
        # 2. Call business service to stop stream
        # 3. Return empty response
        try:
            tenant_id = request.context.tenant_id
            stream_id = request.stream_id

            logger.info(f"StopDataStream request for {stream_id} from tenant {tenant_id}")

            success = await self.business_service.stop_stream(
                stream_id=stream_id,
                tenant_id=tenant_id
            )

            if not success:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Stream not found or unauthorized")

            return common_pb2.Empty()

        except Exception as e:
            logger.error(f"StopDataStream error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.Empty()

    async def GetStreamStatus(self, request, context):
        """
        Get status of a running stream

        Args:
            request: StreamStatusRequest from proto
            context: gRPC context

        Returns:
            StreamStatusResponse
        """
        # TODO: Implement GetStreamStatus
        # 1. Validate stream ownership
        # 2. Call business service to get status
        # 3. Return status response
        try:
            tenant_id = request.context.tenant_id
            stream_id = request.stream_id

            status = await self.business_service.get_stream_status(
                stream_id=stream_id,
                tenant_id=tenant_id
            )

            if "error" in status:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(status["error"])
                return ingestion_pb2.StreamStatusResponse()

            return ingestion_pb2.StreamStatusResponse(
                stream_id=status["stream_id"],
                is_active=status["is_active"],
                symbols=status["symbols"],
                events_processed=status["events_processed"],
                health_status="healthy" if status["is_active"] else "stopped"
            )

        except Exception as e:
            logger.error(f"GetStreamStatus error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ingestion_pb2.StreamStatusResponse()


    async def FetchHistoricalData(self, request, context):
        """
        Fetch historical market data

        Args:
            request: HistoricalDataRequest from proto
            context: gRPC context

        Returns:
            HistoricalDataResponse
        """
        # TODO: Implement FetchHistoricalData
        # 1. Validate tenant context
        # 2. Call business service to fetch data
        # 3. Return historical data
        try:
            tenant_id = request.context.tenant_id

            from datetime import datetime
            start_time = datetime.fromtimestamp(request.start_time.seconds)
            end_time = datetime.fromtimestamp(request.end_time.seconds)

            logger.info(f"FetchHistoricalData request for {request.symbol}")

            candles = await self.business_service.fetch_historical_data(
                tenant_id=tenant_id,
                symbol=request.symbol,
                exchange=request.exchange,
                start_time=start_time,
                end_time=end_time,
                interval=request.interval,
                limit=request.limit or 500
            )

            # Convert to proto messages
            data_points = []
            for candle in candles:
                point = ingestion_pb2.MarketDataPoint(
                    symbol=candle["symbol"],
                    timestamp=common_pb2.Timestamp(seconds=candle["timestamp"] // 1000),
                    price=candle.get("close", 0),
                    volume=candle.get("volume", 0)
                )
                data_points.append(point)

            return ingestion_pb2.HistoricalDataResponse(
                data=data_points,
                total_count=len(data_points)
            )

        except Exception as e:
            logger.error(f"FetchHistoricalData error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ingestion_pb2.HistoricalDataResponse()


async def serve(port: int, business_service):
    """
    Start the gRPC server

    Args:
        port: Port to listen on
        business_service: Business service instance
    """
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    ingestion_pb2_grpc.add_IngestionServiceServicer_to_server(
        IngestionServiceServicer(business_service), server
    )
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info(f"gRPC server started on port {port}")
    await server.wait_for_termination()


# TODO: Implement error handling for gRPC calls
# TODO: Add request validation
# TODO: Add logging and metrics
# TODO: Add authentication check from metadata
