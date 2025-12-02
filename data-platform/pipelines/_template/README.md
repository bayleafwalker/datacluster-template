# Data Platform - Pipeline Template

This directory contains the complete template for creating new data pipelines.

## Quick Start

### 1. Copy Template

```bash
cd data-platform/pipelines
cp -r _template/ my_new_pipeline/
cd my_new_pipeline
```

### 2. Customize Configuration

Edit `config/pipeline.yaml`:
- Update pipeline name, owner, description
- Configure storage paths
- Set resource requirements
- Define quality thresholds

### 3. Define Schemas

Edit schemas in `schemas/`:
- `landing.avsc`: Input data schema
- `curated.avsc`: Output data schema

Use Avro format for schema validation.

### 4. Implement Business Logic

Edit Python scripts in `src/`:
- `landing.py`: Data ingestion logic
- `transform.py`: Business transformations
- `integration.py`: Data publishing

Use common libraries from `data_platform.common.*`

### 5. Create Tests

Edit `tests/`:
- `test_integration.py`: End-to-end tests
- `generators/test_data.py`: Customize test data generation

Run tests:
```bash
pytest tests/ -v
```

### 6. Update Documentation

Edit `docs/`:
- `README.md`: Pipeline overview, SLAs, ownership
- `runbook.md`: Operations guide, troubleshooting

### 7. Configure Kubernetes

Edit `k8s/` manifests:
- Update image references
- Update mainApplicationFile paths
- Adjust resource limits based on `config/pipeline.yaml`

### 8. Deploy

```bash
# Build Docker image
cd data-platform
docker build -t ghcr.io/<user>/datacluster-data:<version> -f Dockerfile .
docker push ghcr.io/<user>/datacluster-data:<version>

# Deploy pipeline
kubectl apply -f pipelines/my_new_pipeline/k8s/
```

## Template Structure

```
_template/
├── config/
│   └── pipeline.yaml       # Pipeline configuration
├── schemas/
│   ├── landing.avsc        # Input schema (Avro)
│   └── curated.avsc        # Output schema (Avro)
├── src/
│   ├── landing.py          # Stage 1: Data ingestion
│   ├── transform.py        # Stage 2: Business logic
│   └── integration.py      # Stage 3: Data publishing
├── tests/
│   ├── test_integration.py # End-to-end tests
│   └── generators/
│       └── test_data.py    # Test data generator
├── k8s/
│   ├── landing.yaml        # SparkApplication for landing
│   └── transform.yaml      # SparkApplication for transform
└── docs/
    ├── README.md           # Pipeline documentation
    └── runbook.md          # Operations guide
```

## Pipeline Stages

### Stage 1: Landing (Ingestion)
- **Purpose**: Read raw data, minimal validation, write to landing storage
- **Input**: Source system (Kafka, S3, DB)
- **Output**: `s3://datacluster-landing/processed/<pipeline>/`
- **Schema**: `schemas/landing.avsc`

### Stage 2: Transform (Business Logic)
- **Purpose**: Apply business rules, aggregations, enrichment
- **Input**: Landing storage
- **Output**: `s3://datacluster-curated/<pipeline>/v1/`
- **Schema**: `schemas/curated.avsc`

### Stage 3: Integration (Publishing)
- **Purpose**: Publish to downstream consumers
- **Input**: Curated storage
- **Output**: Kafka / API / Database

## Using Common Libraries

### Connectors

```python
from data_platform.common.connectors.s3 import S3Reader, S3Writer
from data_platform.common.connectors.kafka import KafkaSparkReader

reader = S3Reader(spark)
df = reader.read_parquet("s3a://bucket/path")

writer = S3Writer()
writer.write_parquet(df, "s3a://bucket/output", partition_by=["date"])
```

### Data Quality

```python
from data_platform.common.transforms.quality import DataQualityChecker

checker = DataQualityChecker()
report = checker.run_all_checks(df, quality_config)
```

### Delta Lake

```python
from data_platform.common.storage.delta import DeltaManager

manager = DeltaManager()
manager.upsert(spark, target_path, source_df, merge_keys=["id"])
```

## Testing

### Generate Test Data

```bash
python tests/generators/test_data.py \
  --output /tmp/test_data.json \
  --count 1000 \
  --edge-cases
```

### Run Unit Tests

```bash
pytest tests/test_integration.py -v
```

### Run Integration Tests

```bash
# Start local Spark cluster
docker-compose up -d

# Run pipeline with test data
spark-submit src/landing.py --input /tmp/test_data.json

# Verify output
ls -lh /tmp/output/
```

## Deployment Checklist

- [ ] Updated `config/pipeline.yaml` with correct settings
- [ ] Defined schemas in `schemas/`
- [ ] Implemented business logic in `src/`
- [ ] Created test data generator in `tests/generators/`
- [ ] Written integration tests in `tests/`
- [ ] Documented pipeline in `docs/README.md`
- [ ] Created runbook in `docs/runbook.md`
- [ ] Updated K8s manifests in `k8s/`
- [ ] Built and pushed Docker image
- [ ] Deployed to cluster
- [ ] Verified monitoring dashboards
- [ ] Set up alerts

## Best Practices

1. **Always define schemas first** - Use Avro for validation
2. **Write tests before deploying** - Catch issues early
3. **Use common libraries** - Don't reinvent the wheel
4. **Document everything** - Future you will thank you
5. **Monitor from day one** - Set up dashboards and alerts
6. **Partition data properly** - By date for time-series data
7. **Use Delta Lake for curated data** - ACID guarantees
8. **Separate concerns** - Landing, transform, integration stages
9. **Version your pipelines** - Semantic versioning in config
10. **Test with edge cases** - Handle nulls, duplicates, etc.

## Troubleshooting

See `docs/runbook.md` for detailed troubleshooting guide.

Common issues:
- **ImagePullBackOff**: Check image exists and credentials
- **Pending pods**: Insufficient resources
- **OOMKilled**: Increase executor memory
- **Data quality failures**: Check upstream data sources

## Support

- **Team**: Data Platform
- **Slack**: #data-platform
- **Issues**: GitHub Issues

---

**Last Updated**: 2025-12-02  
**Version**: 1.0
