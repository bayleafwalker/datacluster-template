# Data Pipeline Strategy & Architecture

## Overview

This document defines the separation strategy between infrastructure and data workloads, establishing a scalable, maintainable structure for data pipelines on the Datacluster platform.

## Core Principles

1. **Separation of Concerns**: Infrastructure (K8s, monitoring) is completely separate from data pipelines
2. **Storage Isolation**: Landing, processing, and curated data use separate storage locations
3. **Reusability**: Common libraries handle standard patterns (connectors, transformations, quality checks)
4. **Testability**: Every pipeline includes test data generators and integration tests
5. **Documentation-First**: Each pipeline requires comprehensive documentation before deployment
6. **Schema-Driven**: All data structures are explicitly defined with version-controlled schemas

---

## Directory Structure

```
datacluster/
├── infrastructure/           # Platform components (NEVER mixed with data)
│   ├── monitoring/          # Prometheus, Grafana
│   ├── spark-operator/      # Spark CRDs and operator
│   ├── storage/             # CSI drivers, S3 configs
│   └── workflows/           # Argo Workflows (optional)
│
├── data-platform/           # NEW: All data pipeline code
│   ├── common/              # Shared libraries
│   │   ├── connectors/      # Source/sink connectors
│   │   │   ├── kafka/
│   │   │   ├── s3/
│   │   │   ├── jdbc/
│   │   │   ├── files/       # CSV, JSON, Parquet
│   │   │   └── streaming/   # Common streaming patterns
│   │   ├── transforms/      # Reusable transformations
│   │   │   ├── quality/     # Data quality checks
│   │   │   ├── deduplication/
│   │   │   ├── enrichment/
│   │   │   └── aggregations/
│   │   ├── storage/         # Storage management
│   │   │   ├── delta/       # Delta Lake patterns
│   │   │   ├── iceberg/     # Apache Iceberg (future)
│   │   │   └── transactional/
│   │   ├── monitoring/      # Custom metrics, logging
│   │   ├── testing/         # Test utilities, fixtures
│   │   └── schemas/         # Shared schema definitions
│   │
│   ├── pipelines/           # Individual data pipelines
│   │   ├── user_analytics/  # Example pipeline
│   │   │   ├── schemas/
│   │   │   │   ├── landing.avsc     # Input schema (Avro)
│   │   │   │   └── curated.avsc     # Output schema
│   │   │   ├── src/
│   │   │   │   ├── landing.py       # Stage 1: Data ingestion
│   │   │   │   ├── transform.py     # Stage 2: Business logic
│   │   │   │   └── integration.py   # Stage 3: Publish to consumers
│   │   │   ├── k8s/
│   │   │   │   ├── landing.yaml     # SparkApplication for landing
│   │   │   │   ├── transform.yaml   # SparkApplication for transform
│   │   │   │   └── workflow.yaml    # Argo DAG (orchestration)
│   │   │   ├── tests/
│   │   │   │   ├── test_landing.py
│   │   │   │   ├── test_transform.py
│   │   │   │   └── generators/
│   │   │   │       ├── test_data.py # Synthetic data generator
│   │   │   │       └── fixtures.py  # Test fixtures
│   │   │   ├── docs/
│   │   │   │   ├── README.md        # Pipeline overview
│   │   │   │   ├── architecture.md  # Design decisions
│   │   │   │   └── runbook.md       # Operations guide
│   │   │   └── config/
│   │   │       └── pipeline.yaml    # Pipeline configuration
│   │   │
│   │   ├── sales_etl/       # Another pipeline (same structure)
│   │   └── _template/       # Pipeline starter template
│   │
│   ├── generators/          # Global test data generators
│   │   ├── kafka_producer.py
│   │   ├── file_generator.py
│   │   └── db_seeder.py
│   │
│   ├── Dockerfile           # Multi-stage build for all pipelines
│   ├── requirements.txt     # Python dependencies
│   └── setup.py             # Package common libraries
│
└── storage/                 # Storage organization (S3/Volumes)
    ├── landing/             # Raw ingestion (separate bucket/volume)
    ├── staging/             # Intermediate processing
    ├── curated/             # Production-ready outputs
    ├── archive/             # Historical data
    └── checkpoints/         # Streaming state
```

---

## Storage Architecture

### Storage Separation Strategy

| Zone | Purpose | Technology | Retention | Access Pattern |
|------|---------|------------|-----------|----------------|
| **Landing** | Raw data ingestion | Hetzner Object Storage (S3) | 7 days | Write-once, append-only |
| **Staging** | Processing intermediate data | Hetzner Volumes (CSI) | 3 days | Read-write, temporary |
| **Curated** | Production datasets | Hetzner Object Storage (S3) | 365 days | Read-optimized, partitioned |
| **Archive** | Historical compliance data | Hetzner Object Storage (S3) | 7 years | Cold storage, infrequent access |
| **Checkpoints** | Streaming state | Hetzner Volumes (CSI) | While job active | High-IOPS, stateful |

### S3 Bucket Structure

```
s3://datacluster-landing/
├── raw/
│   ├── kafka/topic_name/date=YYYY-MM-DD/
│   ├── files/source_system/date=YYYY-MM-DD/
│   └── api/endpoint_name/date=YYYY-MM-DD/

s3://datacluster-curated/
├── analytics/
│   ├── user_metrics/version=v1/date=YYYY-MM-DD/
│   └── sales_aggregates/version=v2/date=YYYY-MM-DD/
├── ml_features/
│   └── customer_embeddings/version=v1/
└── reporting/
    └── daily_summary/date=YYYY-MM-DD/

s3://datacluster-archive/
└── year=YYYY/month=MM/source=*/
```

### Volume (PVC) Structure

```
/data/staging/
├── job_id_1234/        # Isolated per job run
│   ├── temp/
│   └── shuffle/
└── job_id_5678/

/data/checkpoints/
├── streaming_pipeline_1/
│   ├── offsets/
│   ├── state/
│   └── commits/
└── streaming_pipeline_2/
```

---

## Pipeline Component Standards

### 1. Schema Definition

**Required**: Every pipeline MUST define schemas for all inputs/outputs

**Format**: Apache Avro (JSON Schema as fallback for simple cases)

**Example**: `pipelines/user_analytics/schemas/landing.avsc`
```json
{
  "type": "record",
  "name": "UserEvent",
  "namespace": "com.datacluster.analytics",
  "doc": "Raw user event from tracking system",
  "fields": [
    {"name": "event_id", "type": "string", "doc": "UUID"},
    {"name": "user_id", "type": "string"},
    {"name": "event_type", "type": {"type": "enum", "name": "EventType", 
                                     "symbols": ["PAGE_VIEW", "CLICK", "PURCHASE"]}},
    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"},
    {"name": "properties", "type": ["null", {"type": "map", "values": "string"}], "default": null}
  ]
}
```

**Validation**: Use `common/schemas/validator.py` to enforce schema compliance

---

### 2. Pipeline Stages

Every pipeline follows this pattern:

#### Stage 1: Landing (Ingestion)
- **Purpose**: Read raw data from source, apply minimal validation
- **Storage**: Write to `s3://datacluster-landing/raw/<source>/`
- **Schema**: Use landing schema
- **Quality**: Basic checks (non-null keys, record count)
- **File**: `src/landing.py`

#### Stage 2: Transform (Business Logic)
- **Purpose**: Apply business rules, aggregations, enrichment
- **Storage**: Read from landing, write to `s3://datacluster-curated/<domain>/`
- **Schema**: Use curated schema (may differ from landing)
- **Quality**: Full validation, deduplication, referential integrity
- **File**: `src/transform.py`

#### Stage 3: Integration (Publishing)
- **Purpose**: Expose data to consumers (APIs, reports, downstream systems)
- **Storage**: Read from curated, publish to Kafka/DB/Files
- **Schema**: Consumer-specific formats
- **Quality**: SLA checks (latency, completeness)
- **File**: `src/integration.py`

---

### 3. Documentation Requirements

Every pipeline MUST include:

#### `docs/README.md`
```markdown
# Pipeline Name

## Overview
Brief description, business purpose, data sources

## Data Flow
Landing → Transform → Integration (with diagrams)

## Schemas
- Input: Link to schema files
- Output: Link to schema files

## Dependencies
Upstream/downstream pipelines

## SLAs
- Latency: < 1 hour
- Freshness: Updated daily at 2 AM UTC
- Completeness: 99.9%

## Monitoring
- Dashboard: Link to Grafana
- Alerts: Critical conditions

## Ownership
Team: Data Platform
On-call: Slack #data-ops
```

#### `docs/runbook.md`
```markdown
# Operations Runbook

## Deployment
How to deploy changes

## Monitoring
Key metrics to watch

## Troubleshooting
Common issues and fixes

## Emergency Procedures
Data quality failure, pipeline stuck, etc.
```

---

### 4. Test Data Generators

Every pipeline includes synthetic data generation:

**File**: `tests/generators/test_data.py`
```python
from data_platform.common.testing import BaseGenerator
from data_platform.common.schemas import load_schema

class UserEventGenerator(BaseGenerator):
    """Generate synthetic user events matching landing schema"""
    
    def __init__(self, schema_path: str):
        self.schema = load_schema(schema_path)
    
    def generate(self, num_records: int = 1000) -> List[dict]:
        """Generate random but valid events"""
        # Implementation using faker, hypothesis, etc.
        pass
    
    def generate_edge_cases(self) -> List[dict]:
        """Generate boundary conditions for testing"""
        pass
```

**Usage**:
```bash
# Generate test data and run pipeline locally
python tests/generators/test_data.py --output /tmp/test_data --count 10000
spark-submit src/landing.py --input /tmp/test_data
```

---

### 5. Integration Testing

**File**: `tests/test_integration.py`
```python
import pytest
from data_platform.common.testing import SparkTestSession

@pytest.fixture
def spark():
    return SparkTestSession.get_or_create()

def test_end_to_end_pipeline(spark):
    """Test full pipeline: landing → transform → integration"""
    # 1. Generate test data
    test_data = UserEventGenerator("schemas/landing.avsc").generate(1000)
    
    # 2. Run landing
    landing_df = run_landing(spark, test_data)
    assert landing_df.count() == 1000
    
    # 3. Run transform
    transformed_df = run_transform(spark, landing_df)
    assert transformed_df.count() > 0
    
    # 4. Validate schema
    validate_schema(transformed_df, "schemas/curated.avsc")
    
    # 5. Check data quality
    assert check_no_duplicates(transformed_df, ["user_id", "date"])
```

---

## Common Library Functions

### Connectors

#### Kafka Connector (`common/connectors/kafka/`)

```python
# common/connectors/kafka/producer.py
from confluent_kafka import Producer
from data_platform.common.schemas import validate_avro

class KafkaProducer:
    """Generic Kafka producer with schema validation"""
    
    def __init__(self, bootstrap_servers: str, topic: str, schema_path: str):
        self.producer = Producer({'bootstrap.servers': bootstrap_servers})
        self.topic = topic
        self.schema = load_schema(schema_path)
    
    def send(self, key: str, value: dict):
        """Validate and send message"""
        validate_avro(value, self.schema)
        self.producer.produce(self.topic, key=key, value=json.dumps(value))
    
    def flush(self):
        self.producer.flush()

# common/connectors/kafka/consumer.py
class KafkaSparkReader:
    """Read Kafka stream into Spark DataFrame"""
    
    @staticmethod
    def read_stream(spark, bootstrap_servers: str, topic: str, 
                    starting_offsets: str = "latest") -> DataFrame:
        return spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("subscribe", topic) \
            .option("startingOffsets", starting_offsets) \
            .load()
```

#### S3 Connector (`common/connectors/s3/`)

```python
# common/connectors/s3/reader.py
class S3Reader:
    """Read from Hetzner Object Storage with automatic partitioning"""
    
    @staticmethod
    def read_parquet(spark, path: str, partitions: List[str] = None) -> DataFrame:
        """Read parquet with partition pruning"""
        return spark.read.parquet(path)
    
    @staticmethod
    def read_delta(spark, path: str, version: int = None) -> DataFrame:
        """Read Delta Lake table with time travel"""
        if version:
            return spark.read.format("delta").option("versionAsOf", version).load(path)
        return spark.read.format("delta").load(path)

# common/connectors/s3/writer.py
class S3Writer:
    """Write to S3 with best practices (partitioning, compression)"""
    
    @staticmethod
    def write_parquet(df: DataFrame, path: str, mode: str = "overwrite",
                      partition_by: List[str] = None, compression: str = "snappy"):
        """Write with automatic optimization"""
        writer = df.write.mode(mode).option("compression", compression)
        if partition_by:
            writer = writer.partitionBy(*partition_by)
        writer.parquet(path)
```

#### JDBC Connector (`common/connectors/jdbc/`)

```python
# common/connectors/jdbc/reader.py
class JDBCReader:
    """Generic database reader with connection pooling"""
    
    def __init__(self, jdbc_url: str, properties: dict):
        self.jdbc_url = jdbc_url
        self.properties = properties
    
    def read_table(self, spark, table: str, partition_column: str = None,
                   num_partitions: int = 8) -> DataFrame:
        """Read with automatic parallelization"""
        options = {"url": self.jdbc_url, "dbtable": table, **self.properties}
        if partition_column:
            options["partitionColumn"] = partition_column
            options["numPartitions"] = num_partitions
        return spark.read.format("jdbc").options(**options).load()
```

#### File Connector (`common/connectors/files/`)

```python
# common/connectors/files/csv_reader.py
class CSVReader:
    """CSV reader with schema inference and validation"""
    
    @staticmethod
    def read(spark, path: str, schema=None, header: bool = True,
             delimiter: str = ",", infer_schema: bool = False) -> DataFrame:
        """Read CSV with robust options"""
        return spark.read \
            .option("header", header) \
            .option("delimiter", delimiter) \
            .option("inferSchema", infer_schema) \
            .option("mode", "DROPMALFORMED") \
            .schema(schema) \
            .csv(path)
```

### Transformations

#### Data Quality (`common/transforms/quality/`)

```python
# common/transforms/quality/checks.py
class DataQualityChecker:
    """Standard data quality validations"""
    
    @staticmethod
    def check_nulls(df: DataFrame, columns: List[str]) -> dict:
        """Count nulls in specified columns"""
        results = {}
        for col in columns:
            null_count = df.filter(F.col(col).isNull()).count()
            results[col] = null_count
        return results
    
    @staticmethod
    def check_duplicates(df: DataFrame, key_columns: List[str]) -> int:
        """Count duplicate keys"""
        total = df.count()
        distinct = df.select(key_columns).distinct().count()
        return total - distinct
    
    @staticmethod
    def check_referential_integrity(df: DataFrame, ref_df: DataFrame,
                                     join_key: str) -> int:
        """Count orphaned records"""
        orphans = df.join(ref_df, on=join_key, how="left_anti")
        return orphans.count()
```

#### Deduplication (`common/transforms/deduplication/`)

```python
# common/transforms/deduplication/strategies.py
class Deduplicator:
    """Common deduplication patterns"""
    
    @staticmethod
    def keep_latest(df: DataFrame, key_columns: List[str],
                    timestamp_column: str) -> DataFrame:
        """Keep most recent record per key"""
        from pyspark.sql.window import Window
        window = Window.partitionBy(key_columns).orderBy(F.desc(timestamp_column))
        return df.withColumn("row_num", F.row_number().over(window)) \
                 .filter(F.col("row_num") == 1) \
                 .drop("row_num")
    
    @staticmethod
    def aggregate_duplicates(df: DataFrame, key_columns: List[str],
                             agg_functions: dict) -> DataFrame:
        """Aggregate duplicate records"""
        return df.groupBy(key_columns).agg(*[
            func(col).alias(col) for col, func in agg_functions.items()
        ])
```

### Storage Patterns

#### Delta Lake (`common/storage/delta/`)

```python
# common/storage/delta/manager.py
from delta.tables import DeltaTable

class DeltaManager:
    """Delta Lake operations (ACID, time travel, UPSERT)"""
    
    @staticmethod
    def upsert(spark, target_path: str, source_df: DataFrame,
               merge_keys: List[str], update_columns: List[str]):
        """Perform merge (upsert) operation"""
        delta_table = DeltaTable.forPath(spark, target_path)
        
        merge_condition = " AND ".join([f"target.{k} = source.{k}" for k in merge_keys])
        update_set = {col: f"source.{col}" for col in update_columns}
        
        delta_table.alias("target") \
            .merge(source_df.alias("source"), merge_condition) \
            .whenMatchedUpdate(set=update_set) \
            .whenNotMatchedInsertAll() \
            .execute()
    
    @staticmethod
    def time_travel(spark, path: str, timestamp: str) -> DataFrame:
        """Read data as of specific timestamp"""
        return spark.read.format("delta") \
                   .option("timestampAsOf", timestamp) \
                   .load(path)
    
    @staticmethod
    def vacuum(spark, path: str, retention_hours: int = 168):
        """Clean up old versions (default: 7 days)"""
        delta_table = DeltaTable.forPath(spark, path)
        delta_table.vacuum(retention_hours)
```

---

## Pipeline Template

Use `data-platform/pipelines/_template/` as starting point:

```bash
# Create new pipeline
cd data-platform/pipelines
cp -r _template/ my_new_pipeline/

# Customize
cd my_new_pipeline
# Edit config/pipeline.yaml with pipeline parameters
# Define schemas in schemas/
# Implement business logic in src/
# Write tests in tests/
# Document in docs/
```

---

## Deployment Workflow

### 1. Development
```bash
cd data-platform
# Write code using common libraries
from data_platform.common.connectors.kafka import KafkaSparkReader

# Run unit tests
pytest pipelines/user_analytics/tests/test_transform.py

# Run integration tests with test data
pytest pipelines/user_analytics/tests/test_integration.py
```

### 2. Build
```bash
# Build Docker image with all pipelines + common libraries
docker build -t ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-data:0.2.0 -f data-platform/Dockerfile .
docker push ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-data:0.2.0
```

### 3. Deploy
```bash
# Apply SparkApplication manifests (FluxCD or kubectl)
kubectl apply -f data-platform/pipelines/user_analytics/k8s/

# Monitor
kubectl get sparkapplications -n spark-operator
kubectl logs -n spark-operator -l spark-app-name=user-analytics-landing -f
```

### 4. Orchestration (Optional)
```bash
# Deploy Argo Workflow for multi-stage pipeline
kubectl apply -f data-platform/pipelines/user_analytics/k8s/workflow.yaml

# Monitor workflow
kubectl get workflows -n spark-operator
```

---

## Monitoring & Observability

### Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Pipeline latency | Spark metrics | > SLA + 20% |
| Record throughput | Custom counter | < expected rate |
| Data quality violations | Quality checks | > 0.1% |
| Storage usage (landing) | S3 metrics | > 80% quota |
| Storage usage (curated) | S3 metrics | > 70% quota |
| Checkpoint lag (streaming) | Kafka consumer lag | > 10,000 records |

### Grafana Dashboard Structure

**Dashboard**: "Data Pipeline - {pipeline_name}"
- **Row 1**: Pipeline health (status, runtime, last success)
- **Row 2**: Data metrics (records processed, bytes read/written)
- **Row 3**: Quality metrics (validation failures, duplicates)
- **Row 4**: Resource usage (CPU, memory, I/O)
- **Row 5**: Storage (landing size, curated size, growth rate)

---

## Cost Optimization

### Storage Costs
- **Landing**: Auto-delete after 7 days (lifecycle policy)
- **Curated**: Partition by date, archive old partitions to cold storage
- **Checkpoints**: Delete when streaming job terminates

### Compute Costs
- Use Spark dynamic allocation to scale executors
- Schedule batch jobs during off-peak hours
- Destroy worker nodes when not in use (keep control-plane only)

### Current Costs
- **Hetzner Object Storage**: €0.01/GB/month (~€10/month for 1TB)
- **Hetzner Volumes**: €0.05/GB/month (~€10/month for 200GB)
- **Compute**: €11.27/month (2 nodes active) → €6/month (control-plane only when idle)

**Estimated Total**: €20-30/month for moderate workloads (1TB curated, 200GB staging)

---

## Migration Plan

### Phase 1: Common Library Setup (Week 1)
- [ ] Create `data-platform/common/` structure
- [ ] Implement Kafka connector
- [ ] Implement S3 connector with Delta Lake support
- [ ] Implement CSV/File connector
- [ ] Create data quality checker
- [ ] Write tests for all common functions

### Phase 2: Template & Documentation (Week 1)
- [ ] Create pipeline template in `data-platform/pipelines/_template/`
- [ ] Write schema examples (Avro, JSON Schema)
- [ ] Create test data generator utilities
- [ ] Write documentation templates

### Phase 3: Migrate Existing Pipeline (Week 2)
- [ ] Refactor `src/batch_job.py` to use common libraries
- [ ] Split into landing/transform/integration stages
- [ ] Add schemas
- [ ] Add test generators
- [ ] Add comprehensive documentation

### Phase 4: Storage Separation (Week 2)
- [ ] Create separate S3 buckets (landing, curated, archive)
- [ ] Set up lifecycle policies
- [ ] Update pipeline configs to use new storage paths
- [ ] Test data isolation

### Phase 5: Production Readiness (Week 3)
- [ ] Set up monitoring dashboards
- [ ] Configure alerting rules
- [ ] Write runbooks for all pipelines
- [ ] Load testing with large datasets
- [ ] Security review (SOPS encryption, IAM policies)

---

## Next Steps

1. **Review this strategy document** with the team
2. **Create issues** for Phase 1-5 tasks
3. **Set up development environment** with common libraries
4. **Start with one pilot pipeline** to validate approach
5. **Iterate and improve** based on learnings

---

## References

- Architecture: `docs/architecture.md`
- Storage setup: `docs/storage-setup.md` (to be created)
- Common library API: `data-platform/common/README.md` (to be created)
- Pipeline examples: `data-platform/pipelines/*/docs/`

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-02  
**Owner**: Data Platform Team
