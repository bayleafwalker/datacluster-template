# Data Platform Common Libraries

Shared utilities, connectors, and transformations for all data pipelines on the Datacluster platform.

## Overview

This package provides reusable components for building data pipelines:

- **Connectors**: Kafka, S3, JDBC, CSV/JSON/Avro readers/writers
- **Transforms**: Data quality checks, deduplication, enrichment
- **Storage**: Delta Lake operations (ACID, time travel, UPSERT)
- **Schemas**: Avro schema validation and management
- **Testing**: Test data generators and Spark test utilities
- **Monitoring**: Custom metrics and logging

## Installation

### Development Mode
```bash
cd data-platform
pip install -e .
```

### Production Mode
```bash
pip install -e .[quality]  # Include data quality tools
```

## Quick Start

### Using Connectors

#### Kafka Stream Reader
```python
from pyspark.sql import SparkSession
from data_platform.common.connectors.kafka import KafkaSparkReader

spark = SparkSession.builder.appName("MyApp").getOrCreate()
reader = KafkaSparkReader(spark)

# Read stream
df = reader.read_stream(
    bootstrap_servers="kafka:9092",
    topics=["user_events"],
    starting_offsets="earliest"
)

# Parse JSON values
from pyspark.sql.types import StructType, StructField, StringType
schema = StructType([
    StructField("user_id", StringType()),
    StructField("event_type", StringType())
])

parsed_df = reader.parse_json_value(df, schema)
```

#### S3 Reader/Writer
```python
from data_platform.common.connectors.s3 import S3Reader, S3Writer

# Read Parquet
reader = S3Reader(spark)
df = reader.read_parquet(
    path="s3a://datacluster-curated/user_metrics/",
    partition_filters={"date": "2025-12-01"}
)

# Write Parquet with partitioning
writer = S3Writer()
writer.write_parquet(
    df=result_df,
    path="s3a://datacluster-curated/output/",
    partition_by=["date", "region"],
    compression="snappy"
)
```

### Data Quality Checks

```python
from data_platform.common.transforms.quality import DataQualityChecker

checker = DataQualityChecker()

# Check for nulls
null_report = checker.check_nulls(df, ["user_id", "event_type"])

# Check duplicates
dup_count = checker.check_duplicates(df, ["user_id", "date"])

# Run all checks
config = {
    "null_checks": ["user_id", "event_type"],
    "duplicate_keys": ["user_id", "date"],
    "value_ranges": {
        "age": {"min": 0, "max": 120}
    }
}
report = checker.run_all_checks(df, config)
```

### Delta Lake Operations

```python
from data_platform.common.storage.delta import DeltaManager

manager = DeltaManager()

# Upsert (merge) data
manager.upsert(
    spark=spark,
    target_path="s3a://bucket/delta_table",
    source_df=updates_df,
    merge_keys=["user_id"],
    update_columns=["name", "email"]
)

# Time travel
historical_df = manager.time_travel(
    spark, 
    "s3a://bucket/delta_table",
    timestamp="2025-12-01"
)

# Optimize table
manager.optimize(spark, "s3a://bucket/delta_table", z_order_by=["user_id"])
```

## Module Structure

```
common/
├── connectors/        # Data source/sink connectors
│   ├── kafka/         # Kafka producer/consumer
│   ├── s3/            # S3 reader/writer
│   ├── jdbc/          # Database connectors
│   └── files/         # CSV/JSON/Avro
├── transforms/        # Data transformations
│   ├── quality/       # Quality checks
│   └── deduplication/ # Dedup strategies
├── storage/           # Storage patterns
│   └── delta/         # Delta Lake operations
├── schemas/           # Schema validation
├── testing/           # Test utilities
└── monitoring/        # Metrics & logging
```

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Formatting
```bash
black common/
```

### Type Checking
```bash
mypy common/
```

## Documentation

- **Strategy**: See `docs/data-pipeline-strategy.md` for overall architecture
- **Pipeline Template**: See `pipelines/_template/` for creating new pipelines
- **Examples**: See `pipelines/*/docs/` for real-world usage

## Contributing

1. Write code using common libraries
2. Add tests for new features
3. Update documentation
4. Run quality checks (black, mypy, pytest)

## API Reference

### Connectors API

#### Kafka
- `KafkaProducer`: Send messages with schema validation
- `KafkaSparkReader`: Read Kafka streams
- `KafkaStreamWriter`: Write Spark streams to Kafka

#### S3
- `S3Reader`: Read Parquet, Delta, CSV, JSON, Avro
- `S3Writer`: Write with partitioning and compression

#### JDBC
- `JDBCReader`: Database reader with parallelization
- `JDBCWriter`: Batch/streaming database writer

### Transforms API

#### Quality
- `DataQualityChecker.check_nulls()`: Validate non-null constraints
- `DataQualityChecker.check_duplicates()`: Find duplicate keys
- `DataQualityChecker.check_completeness()`: Calculate fill rates
- `DataQualityChecker.run_all_checks()`: Execute configured checks

### Storage API

#### Delta Lake
- `DeltaManager.upsert()`: ACID merge operation
- `DeltaManager.time_travel()`: Read historical versions
- `DeltaManager.optimize()`: Compact files and Z-order
- `DeltaManager.vacuum()`: Clean old versions

## Support

- **Issues**: File issues in project repository
- **Slack**: #data-platform channel
- **Email**: data-platform-team@example.com

---

**Version**: 0.1.0  
**Last Updated**: 2025-12-02
