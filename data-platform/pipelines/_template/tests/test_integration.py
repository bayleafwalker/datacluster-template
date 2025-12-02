"""
Integration Tests

End-to-end pipeline testing with generated test data.
"""
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, LongType, MapType
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope="session")
def spark():
    """Create Spark session for testing"""
    spark = SparkSession.builder \
        .appName("PipelineTest") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()
    
    yield spark
    
    spark.stop()


@pytest.fixture
def test_data(spark):
    """Generate test DataFrame"""
    schema = StructType([
        StructField("id", StringType(), False),
        StructField("timestamp", LongType(), False),
        StructField("source_system", StringType(), False),
        StructField("data", MapType(StringType(), StringType()), False)
    ])
    
    data = [
        ("id1", 1234567890000, "system_a", {"field1": "value1"}),
        ("id2", 1234567891000, "system_b", {"field1": "value2"}),
        ("id3", 1234567892000, "system_a", {"field1": "value3"}),
    ]
    
    return spark.createDataFrame(data, schema)


def test_landing_stage(spark, test_data, tmp_path):
    """Test landing stage processes data correctly"""
    # Write test data
    input_path = str(tmp_path / "input")
    test_data.write.parquet(input_path)
    
    # Run landing logic (import and execute)
    # TODO: Refactor landing.py to have testable functions
    # from landing import process_landing
    # result_df = process_landing(spark, input_path, str(tmp_path / "output"))
    
    # Verify output
    # assert result_df.count() == 3
    # assert "ingestion_timestamp" in result_df.columns
    
    pass  # Placeholder


def test_transform_stage(spark, test_data, tmp_path):
    """Test transform stage applies business logic correctly"""
    # TODO: Implement transform testing
    pass


def test_integration_stage(spark, test_data, tmp_path):
    """Test integration stage publishes data correctly"""
    # TODO: Implement integration testing
    pass


def test_end_to_end_pipeline(spark, tmp_path):
    """Test complete pipeline flow"""
    from generators.test_data import TestDataGenerator
    
    # Generate test data
    generator = TestDataGenerator()
    records = generator.generate_batch(100)
    
    # Convert to DataFrame
    # TODO: Run through all stages
    
    # Verify final output
    pass


def test_data_quality_validation(spark, test_data):
    """Test data quality checks catch issues"""
    from data_platform.common.transforms.quality import DataQualityChecker
    
    checker = DataQualityChecker()
    
    # Check nulls
    null_report = checker.check_nulls(test_data, ["id", "timestamp"])
    assert null_report["id"] == 0
    assert null_report["timestamp"] == 0
    
    # Check duplicates
    dup_count = checker.check_duplicates(test_data, ["id"])
    assert dup_count == 0


def test_deduplication(spark):
    """Test deduplication logic"""
    from data_platform.common.transforms.deduplication import Deduplicator
    from pyspark.sql.types import StructType, StructField, StringType, LongType
    
    # Create data with duplicates
    schema = StructType([
        StructField("id", StringType()),
        StructField("timestamp", LongType()),
        StructField("value", StringType())
    ])
    
    data = [
        ("id1", 1000, "old"),
        ("id1", 2000, "new"),
        ("id2", 1000, "value2"),
    ]
    
    df = spark.createDataFrame(data, schema)
    
    # Deduplicate
    result = Deduplicator.keep_latest(df, ["id"], "timestamp")
    
    # Verify
    assert result.count() == 2
    id1_row = result.filter(result.id == "id1").collect()[0]
    assert id1_row.value == "new"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
