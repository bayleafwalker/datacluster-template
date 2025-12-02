"""
Data Quality Checker

Standard validations for data quality monitoring and alerting.
"""
import logging
from typing import List, Dict, Any, Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    Standard data quality validations
    
    Example:
        checker = DataQualityChecker()
        
        # Check for nulls
        null_report = checker.check_nulls(df, ["user_id", "event_type"])
        
        # Check for duplicates
        dup_count = checker.check_duplicates(df, ["user_id", "date"])
        
        # Run all checks
        report = checker.run_all_checks(df, config)
    """
    
    @staticmethod
    def check_nulls(df: DataFrame, columns: List[str]) -> Dict[str, int]:
        """
        Count null values in specified columns
        
        Args:
            df: DataFrame to check
            columns: Columns to validate
            
        Returns:
            Dict mapping column name to null count
        """
        logger.info(f"Checking nulls in columns: {columns}")
        
        results = {}
        for col in columns:
            null_count = df.filter(F.col(col).isNull()).count()
            results[col] = null_count
            
            if null_count > 0:
                logger.warning(f"Found {null_count} nulls in column: {col}")
        
        return results
    
    @staticmethod
    def check_duplicates(df: DataFrame, key_columns: List[str]) -> int:
        """
        Count duplicate records based on key columns
        
        Args:
            df: DataFrame to check
            key_columns: Columns that define uniqueness
            
        Returns:
            Number of duplicate records
        """
        logger.info(f"Checking duplicates on keys: {key_columns}")
        
        total = df.count()
        distinct = df.select(key_columns).distinct().count()
        duplicates = total - distinct
        
        if duplicates > 0:
            logger.warning(f"Found {duplicates} duplicate records")
        
        return duplicates
    
    @staticmethod
    def check_referential_integrity(
        df: DataFrame, 
        ref_df: DataFrame,
        join_key: str
    ) -> int:
        """
        Count orphaned records (foreign key violations)
        
        Args:
            df: DataFrame with foreign keys
            ref_df: Reference DataFrame with primary keys
            join_key: Column name for join
            
        Returns:
            Number of orphaned records
        """
        logger.info(f"Checking referential integrity on: {join_key}")
        
        orphans = df.join(ref_df, on=join_key, how="left_anti")
        orphan_count = orphans.count()
        
        if orphan_count > 0:
            logger.warning(f"Found {orphan_count} orphaned records")
        
        return orphan_count
    
    @staticmethod
    def check_value_range(
        df: DataFrame,
        column: str,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None
    ) -> int:
        """
        Count values outside expected range
        
        Args:
            df: DataFrame to check
            column: Column to validate
            min_value: Minimum acceptable value
            max_value: Maximum acceptable value
            
        Returns:
            Number of out-of-range values
        """
        logger.info(f"Checking value range for column: {column}")
        
        out_of_range = df
        
        if min_value is not None:
            out_of_range = out_of_range.filter(F.col(column) < min_value)
        
        if max_value is not None:
            out_of_range = out_of_range.filter(F.col(column) > max_value)
        
        count = out_of_range.count()
        
        if count > 0:
            logger.warning(f"Found {count} out-of-range values in {column}")
        
        return count
    
    @staticmethod
    def check_completeness(df: DataFrame, threshold: float = 0.95) -> Dict[str, float]:
        """
        Check data completeness (non-null ratio) for all columns
        
        Args:
            df: DataFrame to check
            threshold: Minimum acceptable completeness ratio (0-1)
            
        Returns:
            Dict mapping column to completeness ratio
        """
        logger.info("Checking data completeness")
        
        total_rows = df.count()
        results = {}
        
        for col in df.columns:
            non_null = df.filter(F.col(col).isNotNull()).count()
            completeness = non_null / total_rows if total_rows > 0 else 0
            results[col] = completeness
            
            if completeness < threshold:
                logger.warning(
                    f"Column {col} completeness {completeness:.2%} below threshold {threshold:.2%}"
                )
        
        return results
    
    @staticmethod
    def check_pattern_match(df: DataFrame, column: str, pattern: str) -> int:
        """
        Count values not matching expected pattern (regex)
        
        Args:
            df: DataFrame to check
            column: Column to validate
            pattern: Regex pattern
            
        Returns:
            Number of non-matching values
        """
        logger.info(f"Checking pattern match for column: {column}")
        
        non_matching = df.filter(~F.col(column).rlike(pattern))
        count = non_matching.count()
        
        if count > 0:
            logger.warning(f"Found {count} values not matching pattern in {column}")
        
        return count
    
    @staticmethod
    def run_all_checks(
        df: DataFrame,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run all configured quality checks
        
        Args:
            df: DataFrame to validate
            config: Quality check configuration
            
        Example config:
            {
                "null_checks": ["user_id", "event_type"],
                "duplicate_keys": ["user_id", "date"],
                "value_ranges": {
                    "age": {"min": 0, "max": 120},
                    "amount": {"min": 0}
                },
                "pattern_checks": {
                    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                }
            }
            
        Returns:
            Dict with all check results
        """
        logger.info("Running all quality checks")
        
        results = {
            "total_records": df.count(),
            "checks": {}
        }
        
        # Null checks
        if "null_checks" in config:
            results["checks"]["nulls"] = DataQualityChecker.check_nulls(
                df, config["null_checks"]
            )
        
        # Duplicate checks
        if "duplicate_keys" in config:
            results["checks"]["duplicates"] = DataQualityChecker.check_duplicates(
                df, config["duplicate_keys"]
            )
        
        # Value range checks
        if "value_ranges" in config:
            range_results = {}
            for col, ranges in config["value_ranges"].items():
                range_results[col] = DataQualityChecker.check_value_range(
                    df, col, 
                    ranges.get("min"), 
                    ranges.get("max")
                )
            results["checks"]["value_ranges"] = range_results
        
        # Pattern checks
        if "pattern_checks" in config:
            pattern_results = {}
            for col, pattern in config["pattern_checks"].items():
                pattern_results[col] = DataQualityChecker.check_pattern_match(
                    df, col, pattern
                )
            results["checks"]["patterns"] = pattern_results
        
        # Completeness check
        if config.get("check_completeness", False):
            threshold = config.get("completeness_threshold", 0.95)
            results["checks"]["completeness"] = DataQualityChecker.check_completeness(
                df, threshold
            )
        
        logger.info("✓ Quality checks completed")
        return results
