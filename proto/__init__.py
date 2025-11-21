"""
Protocol Buffer definitions package.

This package contains all gRPC service definitions and generated code
for inter-service communication.

Generated files:
- *_pb2.py: Message classes
- *_pb2_grpc.py: Service stubs and servicers
- *_pb2.pyi: Type hints

To regenerate proto files, run:
    ./scripts/generate_proto.sh
"""

__version__ = "1.0.0"

# Import all proto modules for easier access
try:
    from proto import (
        analytics_pb2,
        analytics_pb2_grpc,
        common_pb2,
        common_pb2_grpc,
        ingestion_pb2,
        ingestion_pb2_grpc,
        notification_pb2,
        notification_pb2_grpc,
        storage_pb2,
        storage_pb2_grpc,
    )

    __all__ = [
        "common_pb2",
        "common_pb2_grpc",
        "ingestion_pb2",
        "ingestion_pb2_grpc",
        "analytics_pb2",
        "analytics_pb2_grpc",
        "storage_pb2",
        "storage_pb2_grpc",
        "notification_pb2",
        "notification_pb2_grpc",
    ]
except ImportError as e:
    # Proto files not generated yet
    import warnings

    warnings.warn(
        f"Proto files not generated yet. Run './scripts/generate_proto.sh' to generate them. Error: {e}"
    )
    __all__ = []
