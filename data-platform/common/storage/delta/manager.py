"""
Delta Lake Manager

Operations for Delta Lake tables including UPSERT, time travel, and optimization.
"""
import logging
from typing import List, Dict, Optional
from pyspark.sql import SparkSession, DataFrame
from delta.tables import DeltaTable

logger = logging.getLogger(__name__)


class DeltaManager:
    """
    Delta Lake operations (ACID, time travel, UPSERT)
    
    Example:
        manager = DeltaManager()
        
        # Upsert data
        manager.upsert(
            spark=spark,
            target_path="s3a://bucket/delta_table",
            source_df=updates_df,
            merge_keys=["user_id"],
            update_columns=["name", "email", "updated_at"]
        )
        
        # Time travel
        historical_df = manager.time_travel(spark, path, timestamp="2025-12-01")
    """
    
    @staticmethod
    def upsert(
        spark: SparkSession,
        target_path: str,
        source_df: DataFrame,
        merge_keys: List[str],
        update_columns: Optional[List[str]] = None
    ):
        """
        Perform merge (upsert) operation on Delta table
        
        Args:
            spark: Active SparkSession
            target_path: S3 path to Delta table
            source_df: DataFrame with updates/inserts
            merge_keys: Columns to match on (join condition)
            update_columns: Columns to update (None = all source columns)
        """
        logger.info(f"Upserting to Delta table: {target_path}")
        
        delta_table = DeltaTable.forPath(spark, target_path)
        
        # Build merge condition
        merge_condition = " AND ".join([
            f"target.{k} = source.{k}" for k in merge_keys
        ])
        
        # Determine update columns
        if update_columns is None:
            update_columns = source_df.columns
        
        update_set = {col: f"source.{col}" for col in update_columns}
        
        # Execute merge
        delta_table.alias("target") \
            .merge(source_df.alias("source"), merge_condition) \
            .whenMatchedUpdate(set=update_set) \
            .whenNotMatchedInsertAll() \
            .execute()
        
        logger.info("✓ Upsert completed")
    
    @staticmethod
    def time_travel(
        spark: SparkSession,
        path: str,
        version: Optional[int] = None,
        timestamp: Optional[str] = None
    ) -> DataFrame:
        """
        Read Delta table as of specific version or timestamp
        
        Args:
            spark: SparkSession
            path: Path to Delta table
            version: Version number
            timestamp: Timestamp string (e.g., "2025-12-01" or "2025-12-01 10:00:00")
            
        Returns:
            DataFrame from historical version
        """
        if version is not None:
            logger.info(f"Reading Delta table version {version}")
            return spark.read.format("delta") \
                .option("versionAsOf", version) \
                .load(path)
        elif timestamp:
            logger.info(f"Reading Delta table as of {timestamp}")
            return spark.read.format("delta") \
                .option("timestampAsOf", timestamp) \
                .load(path)
        else:
            logger.info("Reading latest Delta table version")
            return spark.read.format("delta").load(path)
    
    @staticmethod
    def vacuum(
        spark: SparkSession,
        path: str,
        retention_hours: int = 168
    ):
        """
        Clean up old versions of Delta table
        
        Args:
            spark: SparkSession
            path: Path to Delta table
            retention_hours: Minimum age to retain (default: 7 days)
        """
        logger.info(f"Vacuuming Delta table: {path} (retention: {retention_hours}h)")
        
        delta_table = DeltaTable.forPath(spark, path)
        delta_table.vacuum(retention_hours)
        
        logger.info("✓ Vacuum completed")
    
    @staticmethod
    def optimize(
        spark: SparkSession,
        path: str,
        z_order_by: Optional[List[str]] = None
    ):
        """
        Optimize Delta table (compact small files, Z-ordering)
        
        Args:
            spark: SparkSession
            path: Path to Delta table
            z_order_by: Columns for Z-ordering (co-location)
        """
        logger.info(f"Optimizing Delta table: {path}")
        
        delta_table = DeltaTable.forPath(spark, path)
        
        if z_order_by:
            logger.info(f"Z-ordering by: {z_order_by}")
            delta_table.optimize().executeZOrderBy(*z_order_by)
        else:
            delta_table.optimize().executeCompaction()
        
        logger.info("✓ Optimization completed")
    
    @staticmethod
    def get_history(spark: SparkSession, path: str, limit: int = 20) -> DataFrame:
        """
        Get Delta table history (commits, operations)
        
        Args:
            spark: SparkSession
            path: Path to Delta table
            limit: Number of history entries to return
            
        Returns:
            DataFrame with table history
        """
        logger.info(f"Fetching Delta table history: {path}")
        
        delta_table = DeltaTable.forPath(spark, path)
        return delta_table.history(limit)
    
    @staticmethod
    def delete_where(
        spark: SparkSession,
        path: str,
        condition: str
    ):
        """
        Delete rows matching condition from Delta table
        
        Args:
            spark: SparkSession
            path: Path to Delta table
            condition: SQL-style WHERE condition (e.g., "age < 0")
        """
        logger.info(f"Deleting from Delta table where: {condition}")
        
        delta_table = DeltaTable.forPath(spark, path)
        delta_table.delete(condition)
        
        logger.info("✓ Delete completed")
    
    @staticmethod
    def restore(
        spark: SparkSession,
        path: str,
        version: Optional[int] = None,
        timestamp: Optional[str] = None
    ):
        """
        Restore Delta table to previous version
        
        Args:
            spark: SparkSession
            path: Path to Delta table
            version: Version to restore to
            timestamp: Timestamp to restore to
        """
        logger.info(f"Restoring Delta table: {path}")
        
        delta_table = DeltaTable.forPath(spark, path)
        
        if version is not None:
            delta_table.restoreToVersion(version)
            logger.info(f"✓ Restored to version {version}")
        elif timestamp:
            delta_table.restoreToTimestamp(timestamp)
            logger.info(f"✓ Restored to timestamp {timestamp}")
