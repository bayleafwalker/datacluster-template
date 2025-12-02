"""
Real-time Event Streaming Pipeline (Migrated)

REFACTORED: Migrated from original streaming_job.py
"""
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import window, col, count, avg
from data_platform.common.connectors.kafka import KafkaStreamWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Streaming Pipeline:
    1. Read from rate source (simulates event stream)
    2. Apply windowed aggregations
    3. Write to console and parquet
    """
    
    spark = SparkSession.builder \
        .appName("RealtimeEventStreaming") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints/streaming") \
        .getOrCreate()
    
    logger.info("=== Starting Real-time Event Streaming Job ===")
    
    # ========== SOURCE ==========
    stream_df = spark.readStream \
        .format("rate") \
        .option("rowsPerSecond", 10) \
        .option("numPartitions", 2) \
        .load()
    
    # Add event metadata
    events = stream_df \
        .withColumn("event_id", (col("value") % 5).cast("string")) \
        .withColumn("event_value", (col("value") % 100).cast("integer")) \
        .selectExpr(
            "timestamp",
            "concat('event_type_', event_id) as event_type",
            "event_value"
        )
    
    logger.info("Stream schema:")
    events.printSchema()
    
    # ========== TRANSFORM ==========
    windowed_counts = events \
        .withWatermark("timestamp", "2 minutes") \
        .groupBy(
            window("timestamp", "1 minute"),
            "event_type"
        ) \
        .agg(
            count("*").alias("event_count"),
            avg("event_value").alias("avg_value")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "event_type",
            "event_count",
            "avg_value"
        )
    
    # ========== SINK ==========
    # Console output
    console_query = windowed_counts.writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", "false") \
        .option("numRows", 20) \
        .trigger(processingTime="30 seconds") \
        .start()
    
    logger.info("✓ Console sink started")
    
    # Parquet output
    parquet_query = windowed_counts.writeStream \
        .outputMode("append") \
        .format("parquet") \
        .option("path", "/tmp/datacluster-output/streaming_events") \
        .option("checkpointLocation", "/tmp/checkpoints/streaming_parquet") \
        .trigger(processingTime="1 minute") \
        .start()
    
    logger.info("✓ Parquet sink started")
    logger.info("✓ Checkpoint: /tmp/checkpoints/streaming")
    logger.info("✓ Output: /tmp/datacluster-output/streaming_events")
    
    # Run indefinitely (in production)
    console_query.awaitTermination()


if __name__ == "__main__":
    main()
