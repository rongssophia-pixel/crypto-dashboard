import grpc
import sys
sys.path.insert(0, 'proto')

from proto import ingestion_pb2, ingestion_pb2_grpc, common_pb2

# Connect to ingestion service
channel = grpc.insecure_channel('localhost:50051')
stub = ingestion_pb2_grpc.IngestionServiceStub(channel)

# Start a ticker stream
request = ingestion_pb2.StartStreamRequest(
    context=common_pb2.TenantContext(
        tenant_id="11111111-1111-1111-1111-111111111111",
        user_id="22222222-2222-2222-2222-222222222222"
    ),
    symbols=["BTCUSDT", "ETHUSDT"],
    exchange="binance",
    stream_type="ticker"
)

response = stub.StartDataStream(request)
print(f"Stream started: {response.stream_id}")
print(f"Success: {response.success}")
print(f"Message: {response.message}")