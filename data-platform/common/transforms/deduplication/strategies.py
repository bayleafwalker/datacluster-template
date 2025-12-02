"""
Deduplication Strategies

Remove or aggregate duplicate records based on various strategies.
"""
import logging
from typing import List, Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)


class Deduplicator:
    """
    Common deduplication patterns for Spark DataFrames
    
    Example:
        # Keep most recent record per key
        df = Deduplicator.keep_latest(df, ["user_id"], "timestamp")
        
        # Aggregate duplicates
        df = Deduplicator.aggregate_duplicates(
            df, 
            ["user_id"], 
            {"amount": F.sum, "count": F.count}
        )
    """
    
    @staticmethod
    def keep_latest(
        df: DataFrame,
        key_columns: List[str],
        timestamp_column: str,
        timestamp_desc: bool = True
    ) -> DataFrame:
        """
        Keep most recent (or oldest) record per key
        
        Args:
            df: DataFrame to deduplicate
            key_columns: Columns that define uniqueness
            timestamp_column: Column to determine "latest"
            timestamp_desc: True = keep most recent, False = keep oldest
            
        Returns:
            Deduplicated DataFrame
        """
        logger.info(f"Deduplicating by keeping latest on keys: {key_columns}")
        
        # Create window partitioned by key, ordered by timestamp
        window = Window.partitionBy(key_columns).orderBy(
            F.desc(timestamp_column) if timestamp_desc else F.asc(timestamp_column)
        )
        
        # Add row number and keep only first
        result = df.withColumn("_row_num", F.row_number().over(window)) \
                   .filter(F.col("_row_num") == 1) \
                   .drop("_row_num")
        
        original_count = df.count()
        dedup_count = result.count()
        duplicates = original_count - dedup_count
        
        logger.info(f"Removed {duplicates} duplicates ({dedup_count} unique records)")
        
        return result
    
    @staticmethod
    def keep_first(df: DataFrame, key_columns: List[str]) -> DataFrame:
        """
        Keep first occurrence of each key (arbitrary order)
        
        Args:
            df: DataFrame to deduplicate
            key_columns: Columns that define uniqueness
            
        Returns:
            Deduplicated DataFrame
        """
        logger.info(f"Deduplicating by keeping first on keys: {key_columns}")
        
        # Use dropDuplicates which keeps first occurrence
        result = df.dropDuplicates(key_columns)
        
        original_count = df.count()
        dedup_count = result.count()
        
        logger.info(f"Removed {original_count - dedup_count} duplicates")
        
        return result
    
    @staticmethod
    def aggregate_duplicates(
        df: DataFrame,
        key_columns: List[str],
        agg_functions: Dict[str, Any]
    ) -> DataFrame:
        """
        Aggregate duplicate records instead of removing
        
        Args:
            df: DataFrame to deduplicate
            key_columns: Columns that define uniqueness
            agg_functions: Dict mapping column name to aggregation function
            
        Example:
            agg_functions = {
                "amount": F.sum,
                "transactions": F.count,
                "last_update": F.max
            }
            
        Returns:
            Aggregated DataFrame
        """
        logger.info(f"Aggregating duplicates on keys: {key_columns}")
        
        # Build aggregation expressions
        agg_exprs = [
            func(col).alias(col) for col, func in agg_functions.items()
        ]
        
        result = df.groupBy(key_columns).agg(*agg_exprs)
        
        original_count = df.count()
        agg_count = result.count()
        
        logger.info(f"Aggregated {original_count} records into {agg_count} unique keys")
        
        return result
    
    @staticmethod
    def mark_duplicates(
        df: DataFrame,
        key_columns: List[str],
        duplicate_flag_column: str = "is_duplicate"
    ) -> DataFrame:
        """
        Mark duplicate records without removing them
        
        Args:
            df: DataFrame to check
            key_columns: Columns that define uniqueness
            duplicate_flag_column: Name for boolean flag column
            
        Returns:
            DataFrame with duplicate flag column added
        """
        logger.info(f"Marking duplicates on keys: {key_columns}")
        
        # Count occurrences of each key
        window = Window.partitionBy(key_columns)
        
        result = df.withColumn(
            "_key_count",
            F.count("*").over(window)
        ).withColumn(
            duplicate_flag_column,
            F.col("_key_count") > 1
        ).drop("_key_count")
        
        duplicate_count = result.filter(F.col(duplicate_flag_column)).count()
        
        logger.info(f"Marked {duplicate_count} duplicate records")
        
        return result
    
    @staticmethod
    def dedupe_by_priority(
        df: DataFrame,
        key_columns: List[str],
        priority_column: str,
        priority_order: str = "desc"
    ) -> DataFrame:
        """
        Keep record with highest (or lowest) priority value per key
        
        Args:
            df: DataFrame to deduplicate
            key_columns: Columns that define uniqueness
            priority_column: Column to determine priority
            priority_order: "desc" = keep highest, "asc" = keep lowest
            
        Returns:
            Deduplicated DataFrame
        """
        logger.info(f"Deduplicating by priority on keys: {key_columns}")
        
        window = Window.partitionBy(key_columns).orderBy(
            F.desc(priority_column) if priority_order == "desc" else F.asc(priority_column)
        )
        
        result = df.withColumn("_row_num", F.row_number().over(window)) \
                   .filter(F.col("_row_num") == 1) \
                   .drop("_row_num")
        
        original_count = df.count()
        dedup_count = result.count()
        
        logger.info(f"Kept {dedup_count} records with {'highest' if priority_order == 'desc' else 'lowest'} priority")
        
        return result
    
    @staticmethod
    def dedupe_exact_matches(df: DataFrame) -> DataFrame:
        """
        Remove exact duplicate rows (all columns identical)
        
        Args:
            df: DataFrame to deduplicate
            
        Returns:
            Deduplicated DataFrame
        """
        logger.info("Removing exact duplicate rows")
        
        result = df.distinct()
        
        original_count = df.count()
        dedup_count = result.count()
        
        logger.info(f"Removed {original_count - dedup_count} exact duplicates")
        
        return result
    
    @staticmethod
    def find_duplicate_groups(
        df: DataFrame,
        key_columns: List[str],
        min_group_size: int = 2
    ) -> DataFrame:
        """
        Find and return groups of duplicate records for inspection
        
        Args:
            df: DataFrame to analyze
            key_columns: Columns that define uniqueness
            min_group_size: Minimum duplicates to include in results
            
        Returns:
            DataFrame with duplicate groups and counts
        """
        logger.info(f"Finding duplicate groups on keys: {key_columns}")
        
        # Count occurrences of each key
        duplicate_groups = df.groupBy(key_columns) \
            .agg(F.count("*").alias("duplicate_count")) \
            .filter(F.col("duplicate_count") >= min_group_size) \
            .orderBy(F.desc("duplicate_count"))
        
        num_groups = duplicate_groups.count()
        total_duplicates = duplicate_groups.agg(F.sum("duplicate_count")).collect()[0][0]
        
        logger.info(f"Found {num_groups} duplicate groups with {total_duplicates} total records")
        
        return duplicate_groups
