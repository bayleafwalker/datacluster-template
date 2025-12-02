"""
Kafka Spark Streaming Writer

Write Spark DataFrames to Kafka topics.
"""
import logging
from typing import Optional, Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, to_json, struct

logger = logging.getLogger(__name__)


class KafkaStreamWriter:
    """
    Write Spark streaming DataFrame to Kafka
    
    Example:
        writer = KafkaStreamWriter()
        query = writer.write_stream(
            df=processed_df,
            bootstrap_servers="kafka:9092",
            topic="output_events",
            checkpoint_location="/data/checkpoints/kafka_writer"
        )
        query.awaitTermination()
    """
    
    @staticmethod
    def write_stream(
        df: DataFrame,
        bootstrap_servers: str,
        topic: str,
        checkpoint_location: str,
        output_mode: str = "append",
        key_column: Optional[str] = None,
        value_columns: Optional[list] = None,
        trigger_interval: Optional[str] = None,
        kafka_options: Optional[Dict[str, Any]] = None
    ):
        """
        Write streaming DataFrame to Kafka
        
        Args:
            df: Streaming DataFrame to write
            bootstrap_servers: Kafka broker addresses
            topic: Target topic
            checkpoint_location: Path for checkpointing
            output_mode: "append", "complete", or "update"
            key_column: Column to use as Kafka key (optional)
            value_columns: Columns to include in value (default: all)
            trigger_interval: Processing interval (e.g., "10 seconds")
            kafka_options: Additional Kafka producer options
            
        Returns:
            StreamingQuery object
        """
        logger.info(f"Writing stream to Kafka topic: {topic}")
        
        # Prepare DataFrame for Kafka format
        write_df = df
        
        # Convert value columns to JSON
        if value_columns:
            value_struct = struct(*[col(c) for c in value_columns])
        else:
            value_struct = struct(*df.columns)
        
        write_df = write_df.withColumn("value", to_json(value_struct))
        
        # Add key if specified
        if key_column:
            write_df = write_df.withColumn("key", col(key_column).cast("string"))
        
        # Select only Kafka columns
        select_cols = ["value"]
        if key_column:
            select_cols.insert(0, "key")
        write_df = write_df.select(select_cols)
        
        # Build writer
        writer = write_df.writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("topic", topic) \
            .option("checkpointLocation", checkpoint_location) \
            .outputMode(output_mode)
        
        # Add additional Kafka options
        if kafka_options:
            for key, value in kafka_options.items():
                writer = writer.option(f"kafka.{key}", value)
        
        # Set trigger
        if trigger_interval:
            from pyspark.sql.streaming import Trigger
            writer = writer.trigger(processingTime=trigger_interval)
        
        return writer.start()
    
    @staticmethod
    def write_batch(
        df: DataFrame,
        bootstrap_servers: str,
        topic: str,
        key_column: Optional[str] = None,
        value_columns: Optional[list] = None,
        mode: str = "append"
    ):
        """
        Write batch DataFrame to Kafka
        
        Args:
            df: Batch DataFrame to write
            bootstrap_servers: Kafka broker addresses
            topic: Target topic
            key_column: Column to use as Kafka key
            value_columns: Columns to include in value
            mode: Write mode ("append", "overwrite", etc.)
        """
        logger.info(f"Writing batch to Kafka topic: {topic}")
        
        # Prepare DataFrame
        write_df = df
        
        if value_columns:
            value_struct = struct(*[col(c) for c in value_columns])
        else:
            value_struct = struct(*df.columns)
        
        write_df = write_df.withColumn("value", to_json(value_struct))
        
        if key_column:
            write_df = write_df.withColumn("key", col(key_column).cast("string"))
        
        select_cols = ["value"]
        if key_column:
            select_cols.insert(0, "key")
        write_df = write_df.select(select_cols)
        
        # Write to Kafka
        write_df.write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("topic", topic) \
            .mode(mode) \
            .save()
