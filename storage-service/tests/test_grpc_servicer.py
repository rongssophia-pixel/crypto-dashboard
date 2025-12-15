from unittest.mock import AsyncMock, MagicMock

import pytest
from api.grpc_servicer import StorageServiceServicer

from proto import common_pb2, storage_pb2


@pytest.fixture
def mock_business_service():
    service = AsyncMock()
    service.archive_data.return_value = {
        "archive_id": "id",
        "success": True,
        "message": "ok",
    }
    service.query_archive.return_value = {
        "rows": [{"col": "val"}],
        "column_names": ["col"],
        "row_count": 1,
        "execution_id": "exec-id",
    }
    return service


@pytest.fixture
def servicer(mock_business_service):
    return StorageServiceServicer(mock_business_service)


@pytest.mark.asyncio
class TestStorageServicer:
    async def test_archive_data(self, servicer, mock_business_service):
        request = storage_pb2.ArchiveRequest(
            start_time=common_pb2.Timestamp(seconds=1000),
            end_time=common_pb2.Timestamp(seconds=2000),
            data_type="market_data",
        )
        request.context.user_id = "user-1"

        response = await servicer.ArchiveData(request, MagicMock())

        assert response.success is True
        mock_business_service.archive_data.assert_called_once()

    async def test_query_archive(self, servicer, mock_business_service):
        request = storage_pb2.ArchiveQueryRequest(sql_query="SELECT *", max_results=10)

        response = await servicer.QueryArchive(request, MagicMock())

        assert response.row_count == 1
        assert response.rows[0].values["col"] == "val"
        mock_business_service.query_archive.assert_called_once()
