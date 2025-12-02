"""
Kafka Spark Streaming Reader

Read Kafka streams into Spark DataFrames for processing.
"""
import logging
from typing import Optional, List
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType

logger = logging.getLogger(__name__)


class KafkaSparkReader:
    """
    Read Kafka stream into Spark DataFrame
    
    Example:
        reader = KafkaSparkReader(spark)
        df = reader.read_stream(
            bootstrap_servers="kafka:9092",
            topics=["user_events"],
            starting_offsets="earliest"
        )
        
        # Parse JSON value
        parsed_df = reader.parse_json_value(df, schema)
    """
    
    def __init__(self, spark: SparkSession):
        """
        Initialize Kafka reader
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
    
    def read_stream(
        self, 
        bootstrap_servers: str, 
        topics: List[str],
        starting_offsets: str = "latest",
        consumer_group: Optional[str] = None,
        max_offsets_per_trigger: Optional[int] = None
    ) -> DataFrame:
        """
        Read Kafka stream as Spark DataFrame
        
        Args:
            bootstrap_servers: Comma-separated Kafka broker addresses
            topics: List of topics to subscribe to
            starting_offsets: "earliest", "latest", or JSON string
            consumer_group: Kafka consumer group ID
            max_offsets_per_trigger: Max records per micro-batch
            
        Returns:
            DataFrame with Kafka message schema (key, value, topic, partition, offset, timestamp)
        """
        topic_str = ",".join(topics)
        logger.info(f"Reading Kafka stream from topics: {topic_str}")
        
        reader = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("subscribe", topic_str) \
            .option("startingOffsets", starting_offsets)
        
        if consumer_group:
            reader = reader.option("kafka.group.id", consumer_group)
        
        if max_offsets_per_trigger:
            reader = reader.option("maxOffsetsPerTrigger", max_offsets_per_trigger)
        
        return reader.load()
    
    def read_batch(
        self,
        bootstrap_servers: str,
        topics: List[str],
        starting_offsets: str = "earliest",
        ending_offsets: str = "latest"
    ) -> DataFrame:
        """
        Read Kafka as batch DataFrame (for testing or backfill)
        
        Args:
            bootstrap_servers: Kafka broker addresses
            topics: Topics to read
            starting_offsets: Start position
            ending_offsets: End position
            
        Returns:
            Batch DataFrame with Kafka messages
        """
        topic_str = ",".join(topics)
        logger.info(f"Reading Kafka batch from topics: {topic_str}")
        
        return self.spark.read \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("subscribe", topic_str) \
            .option("startingOffsets", starting_offsets) \
            .option("endingOffsets", ending_offsets) \
            .load()
    
    @staticmethod
    def parse_json_value(df: DataFrame, schema: StructType, value_column: str = "value") -> DataFrame:
        """
        Parse Kafka value column from JSON string to struct
        
        Args:
            df: Kafka DataFrame
            schema: StructType schema for JSON parsing
            value_column: Name of column containing JSON (default: "value")
            
        Returns:
            DataFrame with parsed JSON as columns
        """
        return df.withColumn(
            "parsed_value",
            from_json(col(value_column).cast("string"), schema)
        ).select("key", "parsed_value.*", "topic", "partition", "offset", "timestamp")
    
    @staticmethod
    def extract_metadata(df: DataFrame) -> DataFrame:
        """
        Extract common Kafka metadata columns
        
        Args:
            df: Kafka DataFrame
            
        Returns:
            DataFrame with extracted metadata
        """
        return df.select(
            col("key").cast("string").alias("message_key"),
            col("value").cast("string").alias("message_value"),
            col("topic"),
            col("partition"),
            col("offset"),
            col("timestamp").alias("kafka_timestamp"),
            col("timestampType")
        )
