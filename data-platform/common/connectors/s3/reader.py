"""
S3 Reader (Hetzner Object Storage Compatible)

Read data from S3-compatible storage with Spark optimizations.
"""
import logging
from typing import Optional, List, Dict, Any
from pyspark.sql import SparkSession, DataFrame

logger = logging.getLogger(__name__)


class S3Reader:
    """
    Read from S3-compatible storage (Hetzner Object Storage)
    
    Example:
        reader = S3Reader(spark)
        df = reader.read_parquet(
            path="s3a://datacluster-curated/user_metrics/",
            partition_filters={"date": "2025-12-01"}
        )
    """
    
    def __init__(self, spark: SparkSession):
        """
        Initialize S3 reader
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
    
    def read_parquet(
        self, 
        path: str, 
        partition_filters: Optional[Dict[str, str]] = None,
        columns: Optional[List[str]] = None
    ) -> DataFrame:
        """
        Read Parquet files with partition pruning and column pruning
        
        Args:
            path: S3 path (s3a://bucket/prefix/)
            partition_filters: Dict of partition column filters
            columns: List of columns to read (None = all)
            
        Returns:
            DataFrame with requested data
        """
        logger.info(f"Reading Parquet from: {path}")
        
        reader = self.spark.read.format("parquet")
        
        df = reader.load(path)
        
        # Apply partition filters
        if partition_filters:
            for col, value in partition_filters.items():
                df = df.filter(df[col] == value)
                logger.debug(f"Applied partition filter: {col} = {value}")
        
        # Apply column pruning
        if columns:
            df = df.select(*columns)
            logger.debug(f"Selected columns: {columns}")
        
        return df
    
    def read_delta(
        self,
        path: str,
        version: Optional[int] = None,
        timestamp: Optional[str] = None
    ) -> DataFrame:
        """
        Read Delta Lake table with time travel support
        
        Args:
            path: S3 path to Delta table
            version: Specific version to read (time travel)
            timestamp: Timestamp string for time travel (e.g., "2025-12-01 10:00:00")
            
        Returns:
            DataFrame from Delta table
        """
        logger.info(f"Reading Delta table from: {path}")
        
        reader = self.spark.read.format("delta")
        
        if version is not None:
            reader = reader.option("versionAsOf", version)
            logger.info(f"Reading version: {version}")
        elif timestamp:
            reader = reader.option("timestampAsOf", timestamp)
            logger.info(f"Reading as of: {timestamp}")
        
        return reader.load(path)
    
    def read_csv(
        self,
        path: str,
        header: bool = True,
        delimiter: str = ",",
        schema=None,
        infer_schema: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> DataFrame:
        """
        Read CSV files from S3
        
        Args:
            path: S3 path
            header: Whether CSV has header row
            delimiter: Field delimiter
            schema: StructType schema (recommended over inference)
            infer_schema: Auto-infer schema (slow for large files)
            options: Additional CSV reader options
            
        Returns:
            DataFrame with CSV data
        """
        logger.info(f"Reading CSV from: {path}")
        
        reader = self.spark.read \
            .option("header", header) \
            .option("delimiter", delimiter) \
            .option("inferSchema", infer_schema) \
            .option("mode", "DROPMALFORMED")
        
        if schema:
            reader = reader.schema(schema)
        
        if options:
            for key, value in options.items():
                reader = reader.option(key, value)
        
        return reader.csv(path)
    
    def read_json(
        self,
        path: str,
        schema=None,
        multiline: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> DataFrame:
        """
        Read JSON files from S3
        
        Args:
            path: S3 path
            schema: StructType schema
            multiline: Whether JSON objects span multiple lines
            options: Additional JSON reader options
            
        Returns:
            DataFrame with JSON data
        """
        logger.info(f"Reading JSON from: {path}")
        
        reader = self.spark.read \
            .option("multiLine", multiline)
        
        if schema:
            reader = reader.schema(schema)
        
        if options:
            for key, value in options.items():
                reader = reader.option(key, value)
        
        return reader.json(path)
    
    def read_avro(
        self,
        path: str,
        schema: Optional[str] = None
    ) -> DataFrame:
        """
        Read Avro files from S3
        
        Args:
            path: S3 path
            schema: Avro schema string (optional)
            
        Returns:
            DataFrame with Avro data
        """
        logger.info(f"Reading Avro from: {path}")
        
        reader = self.spark.read.format("avro")
        
        if schema:
            reader = reader.option("avroSchema", schema)
        
        return reader.load(path)
    
    @staticmethod
    def list_partitions(spark: SparkSession, path: str) -> List[str]:
        """
        List available partitions in a partitioned dataset
        
        Args:
            spark: SparkSession
            path: S3 path to partitioned data
            
        Returns:
            List of partition paths
        """
        from pyspark.sql.utils import AnalysisException
        
        try:
            df = spark.read.parquet(path)
            # Get partition columns
            partition_cols = [field.name for field in df.schema.fields if field.name.startswith("_")]
            logger.info(f"Found partition columns: {partition_cols}")
            return partition_cols
        except AnalysisException as e:
            logger.error(f"Failed to list partitions: {e}")
            return []
