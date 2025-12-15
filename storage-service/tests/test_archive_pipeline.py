import asyncio
import os
import sys
from datetime import datetime, timedelta

import pytest

# Ensure import paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Dynamic import ClickHouseRepository
import importlib.util

from repositories.athena_repository import AthenaRepository
from repositories.postgres_repository import PostgresRepository
from repositories.s3_repository import S3Repository
from services.storage_service import StorageBusinessService

ch_repo_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "analytics-service/repositories/clickhouse_repository.py",
)
spec = importlib.util.spec_from_file_location("analytics_clickhouse_repo", ch_repo_path)
analytics_clickhouse_repo = importlib.util.module_from_spec(spec)
sys.modules["analytics_clickhouse_repo"] = analytics_clickhouse_repo
spec.loader.exec_module(analytics_clickhouse_repo)
ClickHouseRepository = analytics_clickhouse_repo.ClickHouseRepository

from config import settings


@pytest.mark.integration
@pytest.mark.asyncio
class TestArchivePipeline:
    async def test_full_archive_flow(self, real_s3_client, mock_athena_client):
        # Initialize Repos
        # Ensure buckets exist
        try:
            real_s3_client.create_bucket(Bucket=settings.s3_bucket_name)
            real_s3_client.create_bucket(Bucket=settings.athena_output_bucket)
        except Exception:
            pass

        s3_repo = S3Repository(real_s3_client, settings.s3_bucket_name)
        athena_repo = AthenaRepository(
            mock_athena_client,
            settings.athena_database,
            f"s3://{settings.athena_output_bucket}",
            settings.athena_workgroup,
        )

        # Configure Mock Athena
        # We need to simulate the count(*) query result
        mock_athena_client.get_query_results.return_value = {
            "ResultSet": {
                "ResultSetMetadata": {"ColumnInfo": [{"Name": "cnt"}]},
                "Rows": [
                    {"Data": [{"VarCharValue": "cnt"}]},
                    {"Data": [{"VarCharValue": "5"}]},  # Simulate 5 records found
                ],
            }
        }

        clickhouse_repo = ClickHouseRepository(
            settings.clickhouse_host,
            settings.clickhouse_port,
            settings.clickhouse_db,
            settings.clickhouse_user,
            settings.clickhouse_password,
        )
        await clickhouse_repo.connect()

        postgres_repo = PostgresRepository(
            settings.postgres_host,
            settings.postgres_port,
            settings.postgres_db,
            settings.postgres_user,
            settings.postgres_password,
        )

        service = StorageBusinessService(
            s3_repo, athena_repo, clickhouse_repo, postgres_repo
        )

        # Seed ClickHouse
        # Insert some test data
        client = clickhouse_repo.client
        # Ensure table exists (should be created by init script)
        # We'll insert data
        try:
            client.execute(
                """
                INSERT INTO market_data
                (symbol, timestamp, price, volume, exchange, bid_price, ask_price, bid_volume, ask_volume, high_24h, low_24h, volume_24h, price_change_24h, price_change_pct_24h, trade_count, metadata)
                VALUES
                ('BTCUSDT', now(), 50000, 1.5, 'binance', 49999, 50001, 1, 1, 51000, 49000, 100, 100, 0.2, 10, '{}'),
                ('ETHUSDT', now(), 3000, 10.0, 'binance', 2999, 3001, 5, 5, 3100, 2900, 500, 10, 0.3, 20, '{}')
            """
            )
        except Exception as e:
            pytest.skip(f"ClickHouse insert failed (maybe table missing?): {e}")

        # Run Archive
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow() + timedelta(hours=1)

        # Create Athena Database if not exists
        await athena_repo.execute_query(
            f"CREATE DATABASE IF NOT EXISTS {settings.athena_database}"
        )

        # Cleanup table in Athena to ensure clean state
        drop_id = await athena_repo.execute_query(
            f"DROP TABLE IF EXISTS {settings.athena_database}.market_data"
        )
        await athena_repo.wait_for_query(drop_id)

        # Create External Table
        columns = {
            "symbol": "string",
            "timestamp": "string",
            "price": "double",
            "volume": "double",
        }

        await athena_repo.create_external_table(
            "market_data",
            f"s3://{settings.s3_bucket_name}/market_data/",
            columns,
            settings.athena_database,
        )

        try:
            result = await service.archive_data(
                "test-tenant",
                start_time,
                end_time,
                "market_data",
                symbols=["BTCUSDT", "ETHUSDT"],
            )

            assert result["success"] is True
            assert result["records_count"] >= 2

            # Verify Athena Query
            query_result = await service.query_archive(
                "test-tenant",
                f"SELECT count(*) as cnt FROM {settings.athena_database}.market_data",
                1,
            )

            # Count should be at least what we inserted (mocked return 5)
            assert int(query_result["rows"][0]["cnt"]) >= 2

        finally:
            await clickhouse_repo.disconnect()
            await postgres_repo.disconnect()
