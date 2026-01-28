"""Athena Repository"""

import asyncio
import logging
import time
from typing import Dict, Optional

import botocore

logger = logging.getLogger(__name__)


class AthenaRepository:
    """Repository for Athena operations."""

    def __init__(
        self, athena_client, database: str, output_location: str, workgroup: str
    ):
        self.athena = athena_client
        self.database = database
        self.output_location = output_location
        self.workgroup = workgroup
        logger.info(
            "AthenaRepository initialized with database=%s, workgroup=%s",
            database,
            workgroup,
        )

    async def create_external_table(
        self,
        table_name: str,
        s3_path: str,
        columns: Dict[str, str],
        partitions: Optional[Dict[str, str]] = None,
        database: str = None,
    ) -> bool:
        """
        Create an external table referencing Parquet files in S3.
        
        Args:
            table_name: Name of the table to create
            s3_path: S3 location (should not include partition keys in path)
            columns: Mapping of column_name -> athena_type (e.g., string, double)
            partitions: Optional mapping of partition_column -> type (e.g., {'year': 'int', 'month': 'int'})
            database: Database name (defaults to self.database)
        
        Returns:
            True if table creation succeeded
        """
        db = database or self.database
        cols = ", ".join([f"{name} {atype}" for name, atype in columns.items()])
        
        # Build SQL with optional partitions
        sql = f"CREATE EXTERNAL TABLE IF NOT EXISTS {db}.{table_name} ({cols})"
        
        if partitions:
            partition_cols = ", ".join([f"{name} {ptype}" for name, ptype in partitions.items()])
            sql += f" PARTITIONED BY ({partition_cols})"
        
        sql += f" STORED AS PARQUET LOCATION '{s3_path}'"
        
        logger.info("Creating Athena table: %s", sql)
        execution_id = await self.execute_query(sql)
        status = await self.wait_for_query(execution_id, timeout=180)
        return status == "SUCCEEDED"

    async def execute_query(
        self, sql: str, output_location: Optional[str] = None
    ) -> str:
        """Start an Athena query and return the execution ID."""
        try:
            response = await asyncio.to_thread(
                self.athena.start_query_execution,
                QueryString=sql,
                QueryExecutionContext={"Database": self.database},
                WorkGroup=self.workgroup,
                ResultConfiguration={
                    "OutputLocation": output_location or self.output_location,
                },
            )
            execution_id = response["QueryExecutionId"]
            logger.info("Started Athena query %s", execution_id)
            return execution_id
        except Exception as exc:
            logger.error("Failed to start Athena query: %s", exc, exc_info=True)
            raise

    async def wait_for_query(
        self, execution_id: str, timeout: int = 300, poll_interval: float = 2.0
    ) -> str:
        """Poll Athena until the query completes or timeout occurs. Returns final state."""
        start_time = time.monotonic()

        while True:
            if time.monotonic() - start_time > timeout:
                logger.error("Athena query %s timed out", execution_id)
                return "TIMEOUT"

            try:
                response = await asyncio.to_thread(
                    self.athena.get_query_execution, QueryExecutionId=execution_id
                )
                status = (
                    response.get("QueryExecution", {})
                    .get("Status", {})
                    .get("State", "UNKNOWN")
                )
                if status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                    logger.info(
                        "Athena query %s finished with status %s", execution_id, status
                    )
                    return status
            except Exception as exc:
                logger.error(
                    "Error polling Athena query %s: %s",
                    execution_id,
                    exc,
                    exc_info=True,
                )
                return "ERROR"

            await asyncio.sleep(poll_interval)

    async def get_query_results(
        self, execution_id: str, max_results: int = 1000
    ) -> Dict:
        """Fetch query results and return rows + column names."""
        try:
            response = await asyncio.to_thread(
                self.athena.get_query_results,
                QueryExecutionId=execution_id,
                MaxResults=max_results,
            )

            column_info = (
                response.get("ResultSet", {})
                .get("ResultSetMetadata", {})
                .get("ColumnInfo", [])
            )
            columns = [col.get("Name") for col in column_info]

            rows = []
            for row in response.get("ResultSet", {}).get("Rows", [])[1:]:  # skip header
                values = [field.get("VarCharValue") for field in row.get("Data", [])]
                rows.append(dict(zip(columns, values)))

            return {
                "rows": rows,
                "column_names": columns,
                "row_count": len(rows),
                "execution_id": execution_id,
            }
        except botocore.exceptions.ClientError as exc:
            logger.error(
                "Failed to fetch Athena results for %s: %s",
                execution_id,
                exc,
                exc_info=True,
            )
            raise
