"""
gRPC Context Helpers
Utilities for working with gRPC context and metadata
"""
from datetime import datetime
from typing import Dict, Any, Optional

from proto import common_pb2


def create_tenant_context(tenant_id: str, user_id: str, roles: list[str]) -> Any:
    """
    Create a TenantContext message for gRPC calls
    
    Args:
        tenant_id: Tenant identifier
        user_id: User identifier
        roles: User roles
        
    Returns:
        common_pb2.TenantContext message
    """
    return common_pb2.TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles
    )


def create_timestamp(dt: Optional[datetime] = None) -> common_pb2.Timestamp:
    """Create a Timestamp message for gRPC calls"""
    if dt is None:
        dt = datetime.utcnow()

    timestamp = int(dt.timestamp())
    nanos = dt.microsecond * 1000

    return common_pb2.Timestamp(
        seconds=timestamp,
        nanos=nanos
    )


def timestamp_to_datetime(ts: common_pb2.Timestamp) -> datetime:
    """Convert gRPC Timestamp to Python datetime"""
    return datetime.fromtimestamp(ts.seconds + ts.nanos / 1e9)


def extract_metadata(context) -> Dict[str, str]:
    """
    Extract metadata from gRPC context
    
    Args:
        context: gRPC context
        
    Returns:
        Dictionary of metadata key-value pairs
    """
    metadata = {}

    if hasattr(context, 'invocation_metadata'):
        for key, value in context.invocation_metadata():
            metadata[key] = value

    return metadata


def add_auth_metadata(metadata: Dict[str, str], token: str) -> Dict[str, str]:
    """
    Add authentication token to metadata
    
    Args:
        metadata: Existing metadata dictionary
        token: JWT token
        
    Returns:
        Updated metadata dictionary
    """
    metadata_copy = metadata.copy()
    metadata_copy['authorization'] = f'Bearer {token}'
    return metadata_copy



