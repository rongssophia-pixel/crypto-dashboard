"""
Ingestion Service gRPC Servicer
Implements the IngestionService gRPC interface
"""

import grpc
from concurrent import futures
import logging

# from proto import ingestion_pb2, ingestion_pb2_grpc, common_pb2
# from services.ingestion_service import IngestionBusinessService

logger = logging.getLogger(__name__)


class IngestionServiceServicer:
    """
    gRPC servicer for Ingestion Service
    Implements ingestion_pb2_grpc.IngestionServiceServicer
    """
    
    def __init__(self, business_service):
        """
        Initialize servicer with business service
        
        Args:
            business_service: IngestionBusinessService instance
        """
        self.business_service = business_service
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
        pass
    
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
        pass
    
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
        pass
    
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
        pass


async def serve(port: int, business_service):
    """
    Start the gRPC server
    
    Args:
        port: Port to listen on
        business_service: Business service instance
    """
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    # ingestion_pb2_grpc.add_IngestionServiceServicer_to_server(
    #     IngestionServiceServicer(business_service), server
    # )
    server.add_insecure_port(f'[::]:{port}')
    await server.start()
    logger.info(f"gRPC server started on port {port}")
    await server.wait_for_termination()


# TODO: Implement error handling for gRPC calls
# TODO: Add request validation
# TODO: Add logging and metrics
# TODO: Add authentication check from metadata

