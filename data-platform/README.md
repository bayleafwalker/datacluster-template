# Datacluster Data Platform

**Unified framework for building, deploying, and managing data pipelines on Kubernetes.**

## Overview

The Data Platform provides:
- **Reusable common libraries** for connectors, transformations, and storage patterns
- **Pipeline templates** with schemas, tests, and documentation
- **Standardized deployment** via Docker and Kubernetes (SparkApplications)
- **Built-in monitoring** and data quality checks
- **Test data generators** for development and CI/CD

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Platform                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Landing    │─▶│  Transform   │─▶│ Integration  │      │
│  │ (Ingestion)  │  │ (Processing) │  │ (Publishing) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  s3://landing      s3://curated        Kafka/API/DB         │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                   Common Libraries                            │
├─────────────────────────────────────────────────────────────┤
│  Connectors  │  Transforms  │  Storage  │  Testing           │
│  • Kafka     │  • Quality   │  • Delta  │  • Generators      │
│  • S3        │  • Dedup     │  • ACID   │  • Fixtures        │
│  • JDBC      │  • Enrich    │  • Time   │  • Assertions      │
│  • Files     │  • Agg       │    Travel │                    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker
- Kubernetes cluster with Spark Operator
- S3-compatible storage (Hetzner Object Storage)
- Python 3.9+

### Installation

```bash
# Clone repository
cd datacluster/data-platform

# Install common libraries in development mode
pip install -e .

# Install with all extras
pip install -e ".[dev,quality]"
```

### Create Your First Pipeline

```bash
# 1. Copy template
cp -r pipelines/_template/ pipelines/my_pipeline/
cd pipelines/my_pipeline

# 2. Customize configuration
vim config/pipeline.yaml

# 3. Define schemas
vim schemas/landing.avsc
vim schemas/curated.avsc

# 4. Implement business logic
vim src/landing.py
vim src/transform.py
vim src/integration.py

# 5. Generate test data
python tests/generators/test_data.py --output /tmp/test.json --count 1000

# 6. Run tests
pytest tests/ -v

# 7. Build Docker image
cd ../..
docker build -t ghcr.io/<user>/datacluster-data:0.1.0 -f Dockerfile .
docker push ghcr.io/<user>/datacluster-data:0.1.0

# 8. Deploy to cluster
kubectl apply -f pipelines/my_pipeline/k8s/
```

## Directory Structure

```
data-platform/
├── common/                  # Shared libraries (installed as package)
│   ├── connectors/          # Source/sink connectors
│   │   ├── kafka/           # Kafka producer/consumer
│   │   ├── s3/              # S3 reader/writer (Hetzner)
│   │   ├── jdbc/            # Database connectors
│   │   └── files/           # CSV, JSON, Avro
│   ├── transforms/          # Reusable transformations
│   │   ├── quality/         # Data quality checks
│   │   └── deduplication/   # Dedup strategies
│   ├── storage/             # Storage patterns
│   │   └── delta/           # Delta Lake operations
│   ├── schemas/             # Schema validation utilities
│   ├── testing/             # Test utilities
│   └── monitoring/          # Metrics and logging
│
├── pipelines/               # Individual data pipelines
│   ├── _template/           # Pipeline starter template
│   │   ├── schemas/         # Avro schemas
│   │   ├── src/             # Pipeline code (3 stages)
│   │   ├── tests/           # Tests + generators
│   │   ├── k8s/             # SparkApplication manifests
│   │   ├── docs/            # Documentation
│   │   └── config/          # Configuration YAML
│   │
│   ├── user_analytics/      # Example: User analytics pipeline
│   └── sales_etl/           # Example: Sales ETL pipeline
│
├── generators/              # Global test data generators
│   ├── kafka_producer.py
│   ├── file_generator.py
│   └── db_seeder.py
│
├── Dockerfile               # Multi-stage build for all pipelines
├── requirements.txt         # Python dependencies
├── setup.py                 # Package configuration
└── README.md                # This file
```

## Storage Architecture

### Storage Zones

| Zone | Purpose | Technology | Path |
|------|---------|------------|------|
| **Landing** | Raw data ingestion | S3 | `s3://datacluster-landing/` |
| **Staging** | Processing temp data | Volumes (CSI) | `/data/staging/` |
| **Curated** | Production datasets | S3 (Delta Lake) | `s3://datacluster-curated/` |
| **Archive** | Historical compliance | S3 | `s3://datacluster-archive/` |
| **Checkpoints** | Streaming state | Volumes (CSI) | `/data/checkpoints/` |

### Data Lifecycle

```
Source → Landing (7d retention) → Curated (365d) → Archive (7y) → Deletion
         └─ Raw validation         └─ Business logic  └─ Compliance
```

## Common Libraries

### Connectors

#### Kafka
```python
from data_platform.common.connectors.kafka import KafkaSparkReader, KafkaStreamWriter

# Read stream
reader = KafkaSparkReader(spark)
df = reader.read_stream("kafka:9092", ["topic"], starting_offsets="earliest")

# Write stream
writer = KafkaStreamWriter()
query = writer.write_stream(df, "kafka:9092", "output_topic", "/checkpoints")
```

#### S3 (Hetzner Object Storage)
```python
from data_platform.common.connectors.s3 import S3Reader, S3Writer

# Read with partition pruning
reader = S3Reader(spark)
df = reader.read_parquet("s3a://bucket/path", partition_filters={"date": "2025-12-01"})

# Write with partitioning
writer = S3Writer()
writer.write_parquet(df, "s3a://bucket/output", partition_by=["date"], compression="snappy")
```

### Data Quality
```python
from data_platform.common.transforms.quality import DataQualityChecker

checker = DataQualityChecker()
report = checker.run_all_checks(df, {
    "null_checks": ["id", "timestamp"],
    "duplicate_keys": ["id", "date"],
    "value_ranges": {"age": {"min": 0, "max": 120}}
})
```

### Delta Lake
```python
from data_platform.common.storage.delta import DeltaManager

manager = DeltaManager()

# Upsert (ACID merge)
manager.upsert(spark, "s3a://bucket/delta_table", updates_df, merge_keys=["id"])

# Time travel
historical = manager.time_travel(spark, "s3a://bucket/delta_table", timestamp="2025-12-01")

# Optimize
manager.optimize(spark, "s3a://bucket/delta_table", z_order_by=["user_id"])
```

## Pipeline Development Workflow

### 1. Design Phase
- Define business requirements and SLAs
- Design data schemas (Avro)
- Plan storage strategy (partitioning, retention)
- Identify data sources and consumers

### 2. Implementation Phase
- Copy pipeline template
- Implement landing stage (ingestion + validation)
- Implement transform stage (business logic)
- Implement integration stage (publishing)
- Use common libraries for standard operations

### 3. Testing Phase
- Generate synthetic test data
- Write unit tests for transformations
- Write integration tests for end-to-end flow
- Test data quality validations
- Test with edge cases (nulls, duplicates, etc.)

### 4. Deployment Phase
- Build Docker image with all pipelines
- Push to container registry
- Update Kubernetes manifests
- Deploy SparkApplications
- Verify in monitoring dashboards

### 5. Operations Phase
- Monitor metrics and alerts
- Review data quality reports
- Optimize performance (resources, partitioning)
- Handle incidents (see runbooks)
- Iterate based on feedback

## Monitoring

### Grafana Dashboards

- **Data Platform Overview**: All pipelines status
- **Pipeline-Specific**: Per-pipeline metrics
- **Data Quality**: Validation failures, completeness
- **Resource Usage**: CPU, memory, storage

### Key Metrics

```promql
# Processing rate
rate(pipeline_records_processed_total{pipeline="my_pipeline"}[5m])

# Latency
pipeline_latency_seconds{pipeline="my_pipeline"}

# Quality violations
rate(pipeline_quality_violations_total{pipeline="my_pipeline"}[5m])

# Storage usage
pipeline_storage_bytes{zone="curated", pipeline="my_pipeline"}
```

### Alerts

- **Critical**: Pipeline failed 3+ times, data quality < 95%
- **Warning**: Latency > SLA + 20%, storage > 80%
- **Info**: New pipeline deployed, config changed

## Best Practices

### Code Organization
- ✅ Use common libraries for standard operations
- ✅ Separate concerns: landing, transform, integration
- ✅ Write reusable functions, avoid copy-paste
- ✅ Add type hints and docstrings

### Data Quality
- ✅ Define schemas explicitly (Avro)
- ✅ Validate at ingestion (landing stage)
- ✅ Check quality after transformations
- ✅ Fail fast on critical issues
- ✅ Log quality metrics for monitoring

### Performance
- ✅ Partition data by date/region
- ✅ Use columnar formats (Parquet, Delta)
- ✅ Enable adaptive query execution
- ✅ Coalesce small files
- ✅ Use broadcast joins for small tables

### Testing
- ✅ Generate realistic test data
- ✅ Test edge cases (nulls, duplicates, large datasets)
- ✅ Run integration tests in CI/CD
- ✅ Validate schemas automatically

### Operations
- ✅ Document SLAs and ownership
- ✅ Write runbooks for troubleshooting
- ✅ Set up monitoring from day one
- ✅ Version pipeline configurations
- ✅ Use Delta Lake for curated data (time travel)

## Troubleshooting

### Common Issues

**Pipeline not starting**
- Check image exists: `docker pull <image>`
- Verify resources available: `kubectl top nodes`
- Check logs: `kubectl describe sparkapplication <name>`

**High latency**
- Increase executor instances
- Optimize Spark configuration
- Check input data size
- Profile with Spark UI

**Data quality failures**
- Review validation rules
- Check upstream data sources
- Investigate schema changes
- Review quality metrics in Grafana

**OOM errors**
- Increase executor memory
- Reduce executor cores (more memory per core)
- Enable memory overhead
- Repartition data earlier

See individual pipeline runbooks for detailed troubleshooting.

## Development

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_integration.py::test_landing_stage -v

# With coverage
pytest tests/ --cov=common --cov-report=html
```

### Code Quality
```bash
# Format code
black common/ pipelines/

# Type checking
mypy common/

# Linting
flake8 common/ pipelines/
```

### Local Development
```bash
# Install in editable mode
pip install -e ".[dev]"

# Run pipeline locally
spark-submit \
  --master local[*] \
  pipelines/my_pipeline/src/landing.py
```

## Documentation

- **Strategy**: `docs/data-pipeline-strategy.md` - Overall architecture and strategy
- **Common Libraries**: `common/README.md` - API reference for shared libraries
- **Pipeline Template**: `pipelines/_template/README.md` - How to create pipelines
- **Individual Pipelines**: `pipelines/*/docs/` - Per-pipeline documentation

## Contributing

1. Create feature branch from `main`
2. Implement changes using common libraries
3. Add tests for new functionality
4. Update documentation
5. Run quality checks (black, mypy, pytest)
6. Submit pull request

## Support

- **Team**: Data Platform
- **Slack**: #data-platform
- **Email**: data-platform@example.com
- **On-call**: Slack #data-ops (for production incidents)

## Roadmap

### Q1 2026
- [ ] Implement Iceberg table format support
- [ ] Add streaming pipeline examples
- [ ] Create CI/CD templates for GitHub Actions
- [ ] Build data catalog integration

### Q2 2026
- [ ] Add dbt integration for SQL transformations
- [ ] Implement data lineage tracking
- [ ] Create data quality framework with Great Expectations
- [ ] Build ML feature store

### Future
- [ ] Real-time data serving layer
- [ ] Multi-cloud support (AWS, GCP)
- [ ] Data mesh patterns and domain ownership
- [ ] Advanced governance (PII detection, masking)

---

**Version**: 0.1.0  
**Last Updated**: 2025-12-02  
**License**: MIT  
**Maintainer**: Data Platform Team
