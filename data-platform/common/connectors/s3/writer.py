"""
S3 Writer (Hetzner Object Storage Compatible)

Write data to S3-compatible storage with best practices.
"""
import logging
from typing import Optional, List, Dict, Any
from pyspark.sql import DataFrame

logger = logging.getLogger(__name__)


class S3Writer:
    """
    Write to S3-compatible storage with optimizations
    
    Example:
        writer = S3Writer()
        writer.write_parquet(
            df=result_df,
            path="s3a://datacluster-curated/user_metrics/",
            partition_by=["date", "region"],
            mode="overwrite"
        )
    """
    
    @staticmethod
    def write_parquet(
        df: DataFrame,
        path: str,
        mode: str = "overwrite",
        partition_by: Optional[List[str]] = None,
        compression: str = "snappy",
        max_records_per_file: Optional[int] = None,
        coalesce: Optional[int] = None
    ):
        """
        Write DataFrame as Parquet with optimizations
        
        Args:
            df: DataFrame to write
            path: S3 destination path
            mode: "overwrite", "append", "error", "ignore"
            partition_by: Columns to partition by
            compression: "none", "snappy", "gzip", "lzo", "brotli", "zstd"
            max_records_per_file: Max records per output file
            coalesce: Number of output files (reduces small files)
        """
        logger.info(f"Writing Parquet to: {path}")
        
        writer = df.write \
            .mode(mode) \
            .option("compression", compression)
        
        if max_records_per_file:
            writer = writer.option("maxRecordsPerFile", max_records_per_file)
        
        # Reduce number of files if specified
        if coalesce:
            df = df.coalesce(coalesce)
            logger.info(f"Coalesced to {coalesce} partitions")
        
        # Partition if specified
        if partition_by:
            writer = writer.partitionBy(*partition_by)
            logger.info(f"Partitioning by: {partition_by}")
        
        writer.parquet(path)
        logger.info(f"✓ Wrote Parquet to {path}")
    
    @staticmethod
    def write_delta(
        df: DataFrame,
        path: str,
        mode: str = "overwrite",
        partition_by: Optional[List[str]] = None,
        merge_schema: bool = False,
        overwrite_schema: bool = False,
        optimize_write: bool = True
    ):
        """
        Write DataFrame as Delta Lake table
        
        Args:
            df: DataFrame to write
            path: S3 destination path
            mode: Write mode
            partition_by: Columns to partition by
            merge_schema: Merge schemas if structure changed
            overwrite_schema: Replace schema entirely
            optimize_write: Enable optimized writes
        """
        logger.info(f"Writing Delta table to: {path}")
        
        writer = df.write \
            .format("delta") \
            .mode(mode) \
            .option("mergeSchema", merge_schema) \
            .option("overwriteSchema", overwrite_schema)
        
        if optimize_write:
            writer = writer.option("dataChange", "true")
        
        if partition_by:
            writer = writer.partitionBy(*partition_by)
            logger.info(f"Partitioning by: {partition_by}")
        
        writer.save(path)
        logger.info(f"✓ Wrote Delta table to {path}")
    
    @staticmethod
    def write_csv(
        df: DataFrame,
        path: str,
        mode: str = "overwrite",
        header: bool = True,
        delimiter: str = ",",
        compression: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Write DataFrame as CSV
        
        Args:
            df: DataFrame to write
            path: S3 destination
            mode: Write mode
            header: Include header row
            delimiter: Field delimiter
            compression: Compression codec
            options: Additional CSV writer options
        """
        logger.info(f"Writing CSV to: {path}")
        
        writer = df.write \
            .mode(mode) \
            .option("header", header) \
            .option("delimiter", delimiter)
        
        if compression:
            writer = writer.option("compression", compression)
        
        if options:
            for key, value in options.items():
                writer = writer.option(key, value)
        
        writer.csv(path)
        logger.info(f"✓ Wrote CSV to {path}")
    
    @staticmethod
    def write_json(
        df: DataFrame,
        path: str,
        mode: str = "overwrite",
        compression: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Write DataFrame as JSON
        
        Args:
            df: DataFrame to write
            path: S3 destination
            mode: Write mode
            compression: Compression codec
            options: Additional JSON writer options
        """
        logger.info(f"Writing JSON to: {path}")
        
        writer = df.write.mode(mode)
        
        if compression:
            writer = writer.option("compression", compression)
        
        if options:
            for key, value in options.items():
                writer = writer.option(key, value)
        
        writer.json(path)
        logger.info(f"✓ Wrote JSON to {path}")
    
    @staticmethod
    def write_avro(
        df: DataFrame,
        path: str,
        mode: str = "overwrite",
        compression: str = "snappy",
        partition_by: Optional[List[str]] = None
    ):
        """
        Write DataFrame as Avro
        
        Args:
            df: DataFrame to write
            path: S3 destination
            mode: Write mode
            compression: Compression codec
            partition_by: Columns to partition by
        """
        logger.info(f"Writing Avro to: {path}")
        
        writer = df.write \
            .format("avro") \
            .mode(mode) \
            .option("compression", compression)
        
        if partition_by:
            writer = writer.partitionBy(*partition_by)
        
        writer.save(path)
        logger.info(f"✓ Wrote Avro to {path}")
