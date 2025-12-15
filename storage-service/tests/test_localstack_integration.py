import pandas as pd
import pyarrow as pa
import pytest
from botocore.exceptions import ClientError
from repositories.athena_repository import AthenaRepository
from repositories.s3_repository import S3Repository


@pytest.mark.integration
@pytest.mark.asyncio
class TestLocalStackIntegration:
    async def test_full_s3_upload_download_cycle(self, real_s3_client):
        # Setup
        bucket = "test-integration-bucket"
        try:
            real_s3_client.create_bucket(Bucket=bucket)
        except ClientError:
            pass  # Bucket might exist

        repo = S3Repository(real_s3_client, bucket)

        # Upload
        data = [{"col1": "val1", "col2": 123}]
        key = "integration/data.parquet"

        uri = await repo.upload_parquet(data, key)

        assert uri == f"s3://{bucket}/{key}"

        # Verify
        response = real_s3_client.get_object(Bucket=bucket, Key=key)
        assert response["ContentLength"] > 0

        # Cleanup
        await repo.delete_object(key)

    async def test_athena_query_on_real_parquet(
        self, real_s3_client, mock_athena_client
    ):
        # Setup Buckets
        data_bucket = "test-athena-data"
        results_bucket = "test-athena-results"
        try:
            real_s3_client.create_bucket(Bucket=data_bucket)
            real_s3_client.create_bucket(Bucket=results_bucket)
        except ClientError:
            pass

        # Create Data
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        s3_repo = S3Repository(real_s3_client, data_bucket)
        await s3_repo.upload_parquet(pa.Table.from_pandas(df), "data/file.parquet")

        # Configure Mock Athena Client
        mock_athena_client.get_query_results.return_value = {
            "ResultSet": {
                "ResultSetMetadata": {"ColumnInfo": [{"Name": "id"}, {"Name": "name"}]},
                "Rows": [
                    # Header
                    {"Data": [{"VarCharValue": "id"}, {"VarCharValue": "name"}]},
                    # Data
                    {"Data": [{"VarCharValue": "1"}, {"VarCharValue": "a"}]},
                    {"Data": [{"VarCharValue": "2"}, {"VarCharValue": "b"}]},
                    {"Data": [{"VarCharValue": "3"}, {"VarCharValue": "c"}]},
                ],
            }
        }

        # Setup Athena Repo
        athena_repo = AthenaRepository(
            mock_athena_client, "test_db", f"s3://{results_bucket}", "primary"
        )

        # Create Database
        await athena_repo.execute_query("CREATE DATABASE IF NOT EXISTS test_db")

        # Ensure table is clean
        drop_id = await athena_repo.execute_query("DROP TABLE IF EXISTS test_db.users")
        await athena_repo.wait_for_query(drop_id)

        # Create Table
        await athena_repo.create_external_table(
            "users",
            f"s3://{data_bucket}/data/",
            {"id": "int", "name": "string"},
            "test_db",
        )

        # Query
        exec_id = await athena_repo.execute_query(
            "SELECT * FROM test_db.users ORDER BY id"
        )
        status = await athena_repo.wait_for_query(exec_id)
        assert status == "SUCCEEDED"

        results = await athena_repo.get_query_results(exec_id)
        assert results["row_count"] == 3

        rows = results["rows"]
        # Find row with id=1
        row_a = next((r for r in rows if r["id"] == "1"), None)
        assert row_a is not None
        assert row_a["name"] == "a"
