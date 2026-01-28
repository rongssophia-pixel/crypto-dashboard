"""S3 Repository"""

import asyncio
import io
import logging
from typing import Dict, List, Sequence, Union

import botocore
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class S3Repository:
    """Repository for S3 operations."""

    def __init__(self, s3_client, bucket_name: str, auto_create_bucket: bool = True):
        self.s3 = s3_client
        self.bucket_name = bucket_name
        logger.info("S3Repository initialized with bucket: %s", bucket_name)
        
        if auto_create_bucket:
            self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create the bucket if it doesn't exist (for LocalStack/local dev)."""
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            logger.info("Bucket '%s' exists", self.bucket_name)
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                logger.info("Bucket '%s' not found, creating...", self.bucket_name)
                try:
                    self.s3.create_bucket(Bucket=self.bucket_name)
                    logger.info("Bucket '%s' created successfully", self.bucket_name)
                except Exception as create_err:
                    logger.error("Failed to create bucket '%s': %s", self.bucket_name, create_err)
                    raise
            else:
                logger.error("Error checking bucket '%s': %s", self.bucket_name, e)
                raise

    async def upload_file(self, file_path: str, s3_key: str) -> str:
        """Upload a local file to S3."""
        try:
            await asyncio.to_thread(
                self.s3.upload_file, file_path, self.bucket_name, s3_key
            )
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info("Uploaded file to %s", s3_uri)
            return s3_uri
        except Exception as exc:
            logger.error("Failed to upload file %s: %s", file_path, exc, exc_info=True)
            raise

    async def upload_parquet(
        self,
        data: Union[pa.Table, "pa.RecordBatch", Sequence[Dict]],
        s3_key: str,
        compression: str = "snappy",
    ) -> str:
        """
        Upload data as Parquet to S3.

        Args:
            data: pyarrow Table/RecordBatch or sequence of dict rows.
            s3_key: destination object key.
            compression: parquet compression codec.
        Returns:
            S3 URI string for the uploaded object.
        """
        try:
            table = (
                data
                if isinstance(data, (pa.Table, pa.RecordBatch))
                else pa.Table.from_pylist(list(data))
            )

            buffer = io.BytesIO()
            pq.write_table(table, buffer, compression=compression)
            buffer.seek(0)

            await asyncio.to_thread(
                self.s3.put_object,
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType="application/octet-stream",
            )
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info("Uploaded parquet to %s", s3_uri)
            return s3_uri
        except Exception as exc:
            logger.error(
                "Failed to upload parquet to %s: %s", s3_key, exc, exc_info=True
            )
            raise

    async def list_objects(self, prefix: str = "") -> List[Dict]:
        """List objects with prefix."""
        results: List[Dict] = []
        continuation_token = None

        try:
            while True:
                kwargs = {"Bucket": self.bucket_name, "Prefix": prefix}
                if continuation_token:
                    kwargs["ContinuationToken"] = continuation_token

                response = await asyncio.to_thread(self.s3.list_objects_v2, **kwargs)
                contents = response.get("Contents", [])
                for obj in contents:
                    results.append(
                        {
                            "key": obj.get("Key"),
                            "size": obj.get("Size"),
                            "last_modified": obj.get("LastModified"),
                        }
                    )

                if response.get("IsTruncated"):
                    continuation_token = response.get("NextContinuationToken")
                else:
                    break

            return results
        except botocore.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "NoSuchBucket":
                logger.warning(
                    "Bucket %s not found when listing objects", self.bucket_name
                )
                return []
            logger.error(
                "Failed to list objects with prefix %s: %s", prefix, exc, exc_info=True
            )
            raise

    async def get_object_metadata(self, s3_key: str) -> Dict:
        """Return object metadata or empty dict if missing."""
        try:
            response = await asyncio.to_thread(
                self.s3.head_object, Bucket=self.bucket_name, Key=s3_key
            )
            return response or {}
        except botocore.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "404":
                return {}
            logger.error(
                "Failed to get metadata for %s: %s", s3_key, exc, exc_info=True
            )
            raise

    async def delete_object(self, s3_key: str) -> bool:
        """Delete an object from S3."""
        try:
            await asyncio.to_thread(
                self.s3.delete_object, Bucket=self.bucket_name, Key=s3_key
            )
            return True
        except Exception as exc:
            logger.error("Failed to delete %s: %s", s3_key, exc, exc_info=True)
            return False

    async def calculate_archive_size(self, prefix: str) -> int:
        """
        Calculate total size of all objects with the given prefix.
        
        Args:
            prefix: S3 prefix to filter objects (e.g., "market_data/year=2024/")
        
        Returns:
            Total size in bytes
        """
        try:
            objects = await self.list_objects(prefix=prefix)
            total_size = sum(obj.get("size", 0) for obj in objects)
            logger.info("Calculated archive size for prefix '%s': %d bytes", prefix, total_size)
            return total_size
        except Exception as exc:
            logger.error("Failed to calculate archive size for prefix %s: %s", prefix, exc, exc_info=True)
            return 0
