"""
User Analytics Batch Pipeline (Migrated)

REFACTORED: This is the migrated version of the original batch_job.py
using the new data-platform common libraries and 3-stage pattern.
"""
import logging
from datetime import datetime, timedelta
import random
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, max as spark_max, min as spark_min
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType
from data_platform.common.connectors.s3 import S3Writer
from data_platform.common.transforms.quality import DataQualityChecker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    User Analytics ETL Pipeline:
    1. Generate sample user event data
    2. Aggregate by user and event type
    3. Write results to storage
    """
    
    spark = SparkSession.builder \
        .appName("UserAnalyticsBatch") \
        .getOrCreate()
    
    logger.info("=== Starting User Analytics Batch Job ===")
    
    # ========== EXTRACT ==========
    logger.info("EXTRACT: Generating sample data...")
    
    schema = StructType([
        StructField("user_id", StringType(), False),
        StructField("event_type", StringType(), False),
        StructField("event_value", IntegerType(), False),
        StructField("timestamp", TimestampType(), False)
    ])
    
    # Generate sample data
    base_time = datetime.now()
    sample_data = []
    
    event_types = ["page_view", "click", "purchase", "search", "logout"]
    user_ids = [f"user_{i:04d}" for i in range(1, 101)]
    
    for i in range(10000):
        sample_data.append((
            random.choice(user_ids),
            random.choice(event_types),
            random.randint(1, 100),
            base_time - timedelta(minutes=random.randint(0, 1440))
        ))
    
    df = spark.createDataFrame(sample_data, schema)
    logger.info(f"Generated {df.count()} events")
    
    df.cache()
    df.show(10, truncate=False)
    
    # ========== VALIDATE ==========
    logger.info("Running data quality checks...")
    
    checker = DataQualityChecker()
    quality_config = {
        "null_checks": ["user_id", "event_type", "timestamp"],
        "check_completeness": True,
        "completeness_threshold": 0.99
    }
    
    quality_report = checker.run_all_checks(df, quality_config)
    logger.info(f"Quality check results: {quality_report}")
    
    # ========== TRANSFORM ==========
    logger.info("TRANSFORM: Aggregating user metrics...")
    
    # User-level aggregation
    user_metrics = df.groupBy("user_id").agg(
        count("*").alias("total_events"),
        count(col("event_type") == "purchase").alias("purchase_count"),
        avg("event_value").alias("avg_event_value"),
        spark_max("event_value").alias("max_event_value"),
        spark_min("timestamp").alias("first_event"),
        spark_max("timestamp").alias("last_event")
    )
    
    logger.info("User Metrics Sample:")
    user_metrics.show(10, truncate=False)
    
    # Event type aggregation
    event_metrics = df.groupBy("event_type").agg(
        count("*").alias("event_count"),
        avg("event_value").alias("avg_value")
    ).orderBy(col("event_count").desc())
    
    logger.info("Event Type Distribution:")
    event_metrics.show(truncate=False)
    
    # ========== LOAD ==========
    logger.info("LOAD: Writing results to storage...")
    
    output_base = "/tmp/datacluster-output"
    
    # Using new S3Writer from common libraries
    writer = S3Writer()
    
    # Write user metrics
    writer.write_parquet(
        df=user_metrics,
        path=f"{output_base}/user_metrics",
        mode="overwrite",
        compression="snappy"
    )
    
    # Write event metrics
    writer.write_parquet(
        df=event_metrics,
        path=f"{output_base}/event_metrics",
        mode="overwrite",
        compression="snappy"
    )
    
    # Write raw events (partitioned)
    writer.write_parquet(
        df=df,
        path=f"{output_base}/raw_events",
        mode="overwrite",
        partition_by=["event_type"],
        compression="snappy"
    )
    
    # ========== SUMMARY ==========
    logger.info("=== Job Summary ===")
    logger.info(f"Total Events Processed: {df.count()}")
    logger.info(f"Unique Users: {user_metrics.count()}")
    logger.info(f"Event Types: {event_metrics.count()}")
    logger.info(f"Output Location: {output_base}")
    logger.info("=== Job Completed Successfully ===")
    
    spark.stop()


if __name__ == "__main__":
    main()
