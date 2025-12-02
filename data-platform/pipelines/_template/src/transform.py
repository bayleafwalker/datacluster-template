"""
Transform Stage - Business Logic

Reads from landing, applies business rules and transformations, writes to curated.
"""
import logging
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from data_platform.common.connectors.s3 import S3Reader, S3Writer
from data_platform.common.transforms.quality import DataQualityChecker
from data_platform.common.transforms.deduplication import Deduplicator
from data_platform.common.storage.delta import DeltaManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Transform pipeline:
    1. Read from landing storage
    2. Apply deduplication
    3. Apply business transformations and aggregations
    4. Run quality checks
    5. Write to curated storage (Delta Lake)
    """
    
    spark = SparkSession.builder \
        .appName("PipelineName-Transform") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()
    
    logger.info("=== Transform Stage Started ===")
    
    # ========== CONFIGURATION ==========
    LANDING_PATH = "s3a://datacluster-landing/processed/pipeline_name/"
    CURATED_PATH = "s3a://datacluster-curated/pipeline_name/v1/"
    
    # ========== EXTRACT ==========
    logger.info("Reading from landing storage...")
    reader = S3Reader(spark)
    
    # Read specific date partition (for incremental processing)
    # TODO: Replace with actual date logic (e.g., from Airflow context)
    from datetime import date
    process_date = date.today().strftime("%Y-%m-%d")
    
    df = reader.read_parquet(
        path=LANDING_PATH,
        partition_filters={"ingestion_date": process_date}
    )
    
    logger.info(f"Read {df.count()} records from landing")
    df.show(5, truncate=False)
    
    # ========== DEDUPLICATE ==========
    logger.info("Deduplicating records...")
    
    # TODO: Define deduplication strategy
    # Keep latest record per ID
    df = Deduplicator.keep_latest(
        df=df,
        key_columns=["id"],  # Replace with actual key columns
        timestamp_column="timestamp"
    )
    
    logger.info(f"After deduplication: {df.count()} records")
    
    # ========== TRANSFORM ==========
    logger.info("Applying business transformations...")
    
    # TODO: Replace with actual business logic
    
    # Example: Aggregation
    result_df = df.groupBy("entity_type", "date") \
        .agg(
            F.count("*").alias("record_count"),
            F.sum("value").alias("total_value"),
            F.avg("value").alias("avg_value"),
            F.min("timestamp").alias("min_timestamp"),
            F.max("timestamp").alias("max_timestamp")
        )
    
    # Example: Add computed columns
    result_df = result_df.withColumn(
        "processing_timestamp",
        F.current_timestamp()
    )
    
    # ========== VALIDATE ==========
    logger.info("Running quality checks on output...")
    checker = DataQualityChecker()
    
    quality_config = {
        "null_checks": ["entity_type", "date", "record_count"],
        "duplicate_keys": ["entity_type", "date"],
        "value_ranges": {
            "record_count": {"min": 0},
            "avg_value": {"min": 0}
        }
    }
    
    quality_report = checker.run_all_checks(result_df, quality_config)
    logger.info(f"Quality report: {quality_report}")
    
    # Fail if duplicates found
    dup_count = quality_report.get("checks", {}).get("duplicates", 0)
    if dup_count > 0:
        raise ValueError(f"Duplicates found: {dup_count}")
    
    # ========== LOAD ==========
    logger.info("Writing to curated storage (Delta Lake)...")
    
    # Write as Delta table for ACID properties
    writer = S3Writer()
    writer.write_delta(
        df=result_df,
        path=CURATED_PATH,
        mode="append",  # or use DeltaManager.upsert() for updates
        partition_by=["date"],
        optimize_write=True
    )
    
    # Optional: Optimize Delta table
    logger.info("Optimizing Delta table...")
    delta_manager = DeltaManager()
    delta_manager.optimize(
        spark=spark,
        path=CURATED_PATH,
        z_order_by=["entity_type"]  # Co-locate frequently queried columns
    )
    
    # ========== SUMMARY ==========
    logger.info("=== Transform Stage Completed ===")
    logger.info(f"Records written: {result_df.count()}")
    logger.info(f"Output location: {CURATED_PATH}")
    
    spark.stop()


if __name__ == "__main__":
    main()
