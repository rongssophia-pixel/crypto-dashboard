import asyncio
from unittest.mock import MagicMock

import pytest
from repositories.s3_repository import S3Repository


@pytest.mark.asyncio
class TestS3Repository:
    async def test_upload_file(self, mock_s3_client):
        repo = S3Repository(mock_s3_client, "test-bucket")
        s3_key = "test/file.txt"

        uri = await repo.upload_file("local/path.txt", s3_key)

        mock_s3_client.upload_file.assert_called_once_with(
            "local/path.txt", "test-bucket", s3_key
        )
        assert uri == "s3://test-bucket/test/file.txt"

    async def test_upload_parquet(self, mock_s3_client):
        repo = S3Repository(mock_s3_client, "test-bucket")
        data = [{"col1": "val1"}, {"col1": "val2"}]
        s3_key = "test/data.parquet"

        uri = await repo.upload_parquet(data, s3_key)

        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["Bucket"] == "test-bucket"
        assert call_args["Key"] == s3_key
        assert call_args["ContentType"] == "application/octet-stream"
        assert uri == "s3://test-bucket/test/data.parquet"

    async def test_list_objects(self, mock_s3_client):
        repo = S3Repository(mock_s3_client, "test-bucket")
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "file1.txt", "Size": 100},
                {"Key": "file2.txt", "Size": 200},
            ]
        }

        results = await repo.list_objects("prefix")

        assert len(results) == 2
        assert results[0]["key"] == "file1.txt"
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket="test-bucket", Prefix="prefix"
        )
