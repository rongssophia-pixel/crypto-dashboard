"""
gRPC Client Factory
Creates and manages gRPC client connections to microservices
"""
import logging
from typing import Optional, Any, Dict
import grpc

from proto import ingestion_pb2_grpc, analytics_pb2_grpc, storage_pb2_grpc, notification_pb2_grpc

logger = logging.getLogger(__name__)

class GRPCClientFactory:
    """
    Factory for creating gRPC client stubs with connection pooling
    """
    
    def __init__(self):
        """Initialize the client factory with connection pool"""
        self._channels: Dict[str, grpc.Channel] = {}
        self._stubs: Dict[str, Any] = {}
        logger.info("GRPCClientFactory initialized")

    def _get_or_create_channel(self, host: str, port: int) -> grpc.Channel:
        """Get existing channel or create new one"""
        key = f"{host}:{port}"

        if key not in self._channels:
            channel = grpc.insecure_channel(
                key,
                options=[
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 10000),
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.max_send_message_length', 10 * 1024 * 1024),  # 10MB
                    ('grpc.max_receive_message_length', 10 * 1024 * 1024),  # 10MB
                ]
            )
            self._channels[key] = channel
            logger.info(f"Created new gRPC channel: {key}")

        return self._channels[key]

    def get_ingestion_client(self, host: str, port: int):
        """
        Get or create an Ingestion Service client
        
        Args:
            host: Service host
            port: Service port
            
        Returns:
            IngestionServiceStub
        """
        key = f"ingestion-{host}:{port}"

        if key not in self._stubs:
            channel = self._get_or_create_channel(host, port)
            self._stubs[key] = ingestion_pb2_grpc.IngestionServiceStub(channel)
            logger.info(f"Created IngestionService stub")

        return self._stubs[key]
    
    def get_analytics_client(self, host: str, port: int):
        """
        Get or create an Analytics Service client
        
        Args:
            host: Service host
            port: Service port
            
        Returns:
            AnalyticsServiceStub
        """
        key = f"analytics-{host}:{port}"

        if key not in self._stubs:
            channel = self._get_or_create_channel(host, port)
            self._stubs[key] = analytics_pb2_grpc.AnalyticsServiceStub(channel)
            logger.info(f"Created AnalyticsService stub")

        return self._stubs[key]
    
    def get_storage_client(self, host: str, port: int):
        """
        Get or create a Storage Service client
        
        Args:
            host: Service host
            port: Service port
            
        Returns:
            StorageServiceStub
        """
        key = f"storage-{host}:{port}"

        if key not in self._stubs:
            channel = self._get_or_create_channel(host, port)
            self._stubs[key] = storage_pb2_grpc.StorageServiceStub(channel)
            logger.info(f"Created StorageService stub")

        return self._stubs[key]
    
    def get_notification_client(self, host: str, port: int):
        """
        Get or create a Notification Service client
        
        Args:
            host: Service host
            port: Service port
            
        Returns:
            NotificationServiceStub
        """
        key = f"notification-{host}:{port}"

        if key not in self._stubs:
            channel = self._get_or_create_channel(host, port)
            self._stubs[key] = notification_pb2_grpc.NotificationServiceStub(channel)
            logger.info(f"Created NotificationService stub")

        return self._stubs[key]
    
    def close_all(self):
        """Close all open gRPC channels"""
        for key, channel in self._channels.items():
            channel.close()
            logger.info(f"Closed channel: {key}")

        self._channels.clear()
        self._stubs.clear()


class GRPCInterceptor(grpc.UnaryUnaryClientInterceptor):
    """
    gRPC client interceptor for adding metadata (auth, tracing, etc.)
    """
    
    def __init__(self, tenant_context: Optional[Any] = None):
        """
        Initialize interceptor
        
        Args:
            tenant_context: Optional tenant context for multi-tenancy
        """
        self.tenant_context = tenant_context
    
    def intercept_unary_unary(self, continuation, client_call_details, request):
        """
        Intercept unary-unary calls to add metadata
        """
        metadata = []

        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)

        # Add tenant context to metadata
        if self.tenant_context:
            metadata.append(('tenant-id', self.tenant_context.tenant_id))
            metadata.append(('user-id', self.tenant_context.user_id))

        # Add request ID for tracing
        import uuid
        request_id = str(uuid.uuid4())
        metadata.append(('request-id', request_id))

        # Create new client call details with updated metadata
        new_details = grpc._interceptor._ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials,
            client_call_details.wait_for_ready,
            client_call_details.compression,
        )

        return continuation(new_details, request)

