# Data Platform Track - AI Coding Agent Instructions

**Context**: Data pipeline development, Spark jobs, analytics

[← Back to AGENTS.md](../../AGENTS.md)

---

## 📊 Data Platform Overview

The data platform provides a framework for building, deploying, and managing data pipelines on Kubernetes using Apache Spark.

**Key Features:**
- Reusable common libraries (connectors, transforms, storage)
- Self-contained project structure
- Standardized testing and deployment
- Multi-environment support (dev/staging/prod)
- Built-in monitoring and data quality checks

---

## 📁 Data Platform Structure

```
data-platform/
├── common/                       # Shared libraries (installed as package)
│   ├── connectors/
│   │   ├── kafka/               # Kafka producer/consumer/streaming
│   │   ├── s3/                  # S3 reader/writer
│   │   ├── jdbc/                # Database connectors
│   │   └── files/               # CSV, JSON, Parquet handlers
│   ├── transforms/
│   │   ├── quality/             # Data quality checks
│   │   └── deduplication/       # Deduplication strategies
│   ├── storage/
│   │   └── delta/               # Delta Lake operations (UPSERT, time travel)
│   └── __init__.py
│
├── projects/                     # Independent pipeline projects
│   ├── _template/               # Project template
│   │   ├── PROJECT.yaml         # Metadata (owner, resources, schedule, SLAs)
│   │   ├── config/              # All configuration centralized
│   │   ├── schemas/             # Avro schemas
│   │   ├── src/                 # Source code (landing, transform, integration)
│   │   ├── tests/               # Unit/integration tests + generators
│   │   ├── k8s/                 # Kubernetes manifests (base + overlays)
│   │   ├── docs/                # Complete documentation
│   │   └── scripts/             # Project-specific automation
│   │
│   ├── user_analytics/          # Example: User behavior analytics
│   └── event_streaming/         # Example: Real-time event processing
│
├── Dockerfile                    # Multi-stage build for all projects
├── requirements.txt              # Python dependencies
├── setup.py                      # Package installer for common libraries
└── README.md                     # Data platform documentation
```

---

## 🔑 Key Workflows

### 1. Create New Project

**From template:**
```bash
# Copy template
cp -r data-platform/projects/_template data-platform/projects/my-pipeline

# Edit metadata
vim data-platform/projects/my-pipeline/PROJECT.yaml

# Fill in:
# - name, version, description
# - owner (team, contacts)
# - dependencies
# - resources (CPU, memory per stage)
# - schedule (cron expressions)
# - storage paths
# - monitoring (alerts, dashboards)

# Configure pipeline
vim data-platform/projects/my-pipeline/config/pipeline.yaml

# Define schemas
vim data-platform/projects/my-pipeline/schemas/v1/landing.avsc
vim data-platform/projects/my-pipeline/schemas/v1/curated.avsc
```

### 2. Develop Pipeline

**Using common libraries:**
```python
# data-platform/projects/my-pipeline/src/landing.py
from pyspark.sql import SparkSession
from data_platform.common.connectors.s3 import S3Reader, S3Writer
from data_platform.common.transforms.quality import DataQualityChecker

def main():
    spark = SparkSession.builder.appName("MyPipeline-Landing").getOrCreate()
    
    # Read from landing zone
    reader = S3Reader()
    df = reader.read_parquet("s3a://datacluster-data/landing/my-data")
    
    # Quality checks
    checker = DataQualityChecker()
    quality_config = {
        "null_checks": ["id", "timestamp"],
        "check_completeness": True
    }
    report = checker.run_all_checks(df, quality_config)
    
    # Write to staging
    writer = S3Writer()
    writer.write_parquet(
        df=df,
        path="s3a://datacluster-data/staging/my-data",
        mode="overwrite",
        partition_by=["date"]
    )
```

### 3. Test Locally

**Run tests:**
```bash
cd data-platform/projects/my-pipeline/
pytest tests/unit/
pytest tests/integration/
```

**Generate test data:**
```bash
python tests/generators/test_data.py --output /tmp/test-data/
```

**Run locally with Spark:**
```bash
cd data-platform
spark-submit \
  --master local[*] \
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
  projects/my-pipeline/src/landing.py \
  --config projects/my-pipeline/config/environments/dev.yaml
```

### 4. Build Docker Image

**Build image (includes all projects):**
```bash
cd data-platform
docker build -t ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-data:0.2.0 .
docker push ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-data:0.2.0
```

**Multi-stage Dockerfile** caches dependencies for fast rebuilds:
- Base stage: Python + Java + Spark
- Dev stage: Testing tools
- Prod stage: Common libs + projects + JMX exporter

### 5. Deploy to Cluster

**Update image in K8s manifests:**
```yaml
# data-platform/projects/my-pipeline/k8s/base/landing.yaml
spec:
  image: "ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-data:0.2.0"  # Update version
  mainApplicationFile: local:///app/projects/my-pipeline/src/landing.py
```

**Deploy to dev:**
```bash
kubectl apply -k data-platform/projects/my-pipeline/k8s/overlays/dev/
```

**Monitor:**
```bash
# Check status
kubectl get sparkapplications -n spark-operator

# Get logs
kubectl logs -f my-pipeline-landing-driver -n spark-operator

# Spark UI
kubectl port-forward svc/my-pipeline-landing-ui-svc 4040:4040 -n spark-operator
# Open http://localhost:4040
```

**Deploy to production (after validation):**
```bash
kubectl apply -k data-platform/projects/my-pipeline/k8s/overlays/prod/
```

---

## 📋 Project Structure Standards

Every project **must** follow this structure:

### Required Files

```
my-pipeline/
├── PROJECT.yaml              # ⭐ Single source of truth
├── README.md                 # Project overview
├── config/
│   ├── pipeline.yaml         # Main pipeline config
│   ├── secrets.yaml.enc      # Encrypted secrets (SOPS)
│   └── environments/
│       ├── dev.yaml          # Dev overrides
│       ├── staging.yaml      # Staging overrides
│       └── prod.yaml         # Production config
├── schemas/
│   └── v1/
│       ├── landing.avsc      # Input schema
│       └── curated.avsc      # Output schema
├── src/
│   ├── landing.py            # Stage 1: Ingestion
│   ├── transform.py          # Stage 2: Processing
│   └── integration.py        # Stage 3: Publishing
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── generators/           # Test data generators
│   └── fixtures/             # Sample data
├── k8s/
│   ├── base/
│   │   ├── landing.yaml
│   │   ├── transform.yaml
│   │   └── kustomization.yaml
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── prod/
└── docs/
    ├── README.md             # Detailed docs
    ├── architecture.md       # Design, data flow
    └── runbook.md            # Operations guide
```

### PROJECT.yaml Template

```yaml
name: "my-pipeline"
version: "0.1.0"
description: "What this pipeline does"

owner:
  team: "data-engineering"
  slack: "#data-eng"
  email: "data-eng@company.com"

dependencies:
  data_platform_common: "^0.5.0"
  python: ">=3.9,<3.12"
  spark: "3.5.0"

resources:
  landing:
    driver: { cpu: "1", memory: "2Gi" }
    executors: { count: 3, cpu: "2", memory: "4Gi" }
  transform:
    driver: { cpu: "2", memory: "4Gi" }
    executors: { count: 5, cpu: "4", memory: "8Gi" }

schedule:
  landing: "*/15 * * * *"       # Every 15 min
  transform: "0 */1 * * *"      # Hourly

sla:
  latency: "30m"
  availability: "99.9%"
  data_quality_threshold: 0.95

storage:
  landing: "s3://datacluster-data/landing/my-pipeline"
  curated: "s3://datacluster-data/curated/my-pipeline"

monitoring:
  grafana_dashboard: "my-pipeline-dashboard"
  alerts:
    - name: "high-failure-rate"
      threshold: 0.1
      severity: "critical"

tags: ["domain", "type", "priority"]
status: "development"  # development | staging | production
```

---

## 🧪 Testing Standards

### Unit Tests

```python
# tests/unit/test_landing.py
import pytest
from pyspark.sql import SparkSession
from src.landing import process_data

@pytest.fixture(scope="session")
def spark():
    return SparkSession.builder \
        .appName("test") \
        .master("local[*]") \
        .getOrCreate()

def test_process_data(spark):
    # Arrange
    input_data = [("user1", 100), ("user2", 200)]
    df = spark.createDataFrame(input_data, ["user_id", "value"])
    
    # Act
    result = process_data(df)
    
    # Assert
    assert result.count() == 2
    assert "processed_value" in result.columns
```

### Integration Tests

```python
# tests/integration/test_end_to_end.py
def test_full_pipeline(spark, test_data_path):
    # Run full pipeline stages
    landing_output = run_landing(spark, test_data_path)
    transform_output = run_transform(spark, landing_output)
    
    # Verify outputs
    assert transform_output.count() > 0
    # Check data quality metrics
    # Verify output schema
```

### Test Data Generators

```python
# tests/generators/test_data.py
from faker import Faker
import random

def generate_events(num_records=1000):
    fake = Faker()
    events = []
    
    for i in range(num_records):
        event = {
            "id": str(i),
            "user_id": f"user_{random.randint(1, 100)}",
            "event_type": random.choice(["click", "view", "purchase"]),
            "timestamp": fake.date_time_this_month().isoformat(),
            "value": random.randint(1, 100)
        }
        events.append(event)
    
    return events
```

---

## 🔄 Common Library Usage

### S3 Connectors

```python
from data_platform.common.connectors.s3 import S3Reader, S3Writer

# Reading
reader = S3Reader()
df = reader.read_parquet("s3a://bucket/path")
df = reader.read_delta("s3a://bucket/path")
df = reader.read_csv("s3a://bucket/path", header=True)

# Writing
writer = S3Writer()
writer.write_parquet(
    df=df,
    path="s3a://bucket/output",
    mode="overwrite",
    partition_by=["date", "region"],
    compression="snappy"
)
```

### Kafka Integration

```python
from data_platform.common.connectors.kafka import KafkaProducer, KafkaStreamWriter

# Batch produce
producer = KafkaProducer(bootstrap_servers="kafka:9092")
producer.send_dataframe(
    df=df,
    topic="events",
    key_column="user_id"
)

# Streaming write
writer = KafkaStreamWriter(bootstrap_servers="kafka:9092")
query = writer.write_stream(
    df=streaming_df,
    topic="analytics-results",
    checkpoint_location="s3a://checkpoints/my-pipeline"
)
```

### Data Quality Checks

```python
from data_platform.common.transforms.quality import DataQualityChecker

checker = DataQualityChecker()

# Define checks
config = {
    "null_checks": ["id", "user_id", "timestamp"],
    "duplicate_check": True,
    "duplicate_columns": ["id"],
    "completeness_threshold": 0.99,
    "referential_integrity": {
        "foreign_key": "user_id",
        "reference_df": users_df,
        "reference_key": "id"
    }
}

# Run all checks
report = checker.run_all_checks(df, config)

# Report structure:
# {
#   "passed": True/False,
#   "total_checks": 5,
#   "passed_checks": 4,
#   "failed_checks": 1,
#   "details": {...}
# }
```

### Delta Lake Operations

```python
from data_platform.common.storage.delta import DeltaManager

delta_mgr = DeltaManager()

# UPSERT (merge)
delta_mgr.upsert(
    df=new_data,
    path="s3a://curated/users",
    merge_keys=["user_id"],
    update_columns=["name", "email"],
    insert_all=True
)

# Time travel
historical_df = delta_mgr.time_travel(
    path="s3a://curated/users",
    version=5  # or timestamp="2025-12-01"
)

# Optimize
delta_mgr.optimize(
    path="s3a://curated/users",
    where="date >= '2025-12-01'"
)

# Vacuum (delete old versions)
delta_mgr.vacuum(
    path="s3a://curated/users",
    retention_hours=168  # 7 days
)
```

### Deduplication

```python
from data_platform.common.transforms.deduplication import Deduplicator

dedup = Deduplicator()

# Keep latest by timestamp
clean_df = dedup.keep_latest(
    df=df,
    partition_columns=["user_id"],
    order_column="timestamp"
)

# Mark duplicates (adds is_duplicate column)
marked_df = dedup.mark_duplicates(
    df=df,
    key_columns=["user_id", "event_id"]
)
```

---

## 📦 Project Management

### List Projects

```bash
./scripts/list-projects.sh

# Output:
# PROJECT              VERSION    STATUS      TEAM
# user-analytics       1.2.0      production  data-engineering
# event-streaming      1.0.0      production  data-engineering
```

### Import External Project

```bash
./scripts/import-project.sh https://github.com/company/fraud-detection

# Validates structure
# Checks dependencies
# Updates metadata
```

### Export Project

```bash
./scripts/export-project.sh user-analytics https://github.com/company/user-analytics.git

# Creates standalone repo
# Generates CI/CD workflows
# Initializes Git
```

---

## 🚀 Deployment Patterns

### Environment-Specific Configs

**Base configuration** (`k8s/base/landing.yaml`):
```yaml
apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication
metadata:
  name: my-pipeline-landing
spec:
  driver:
    cores: 1
    memory: "2Gi"
  executor:
    instances: 3
    cores: 2
    memory: "4Gi"
```

**Dev overlay** (`k8s/overlays/dev/kustomization.yaml`):
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
bases:
  - ../../base
patchesStrategicMerge:
  - patches.yaml
```

**Dev patches** (`k8s/overlays/dev/patches.yaml`):
```yaml
apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication
metadata:
  name: my-pipeline-landing
spec:
  executor:
    instances: 1  # Fewer executors in dev
  sparkConf:
    "spark.sql.shuffle.partitions": "8"  # Less parallelism
```

### Progressive Deployment

```bash
# 1. Deploy to dev
kubectl apply -k k8s/overlays/dev/

# 2. Validate
kubectl get sparkapplications -n spark-operator
kubectl logs -f my-pipeline-landing-driver -n spark-operator

# 3. Run smoke tests
pytest tests/integration/ --env=dev

# 4. Deploy to staging
kubectl apply -k k8s/overlays/staging/

# 5. Validate in staging
# Monitor for 24 hours

# 6. Deploy to production
kubectl apply -k k8s/overlays/prod/

# 7. Monitor closely
# Check Grafana dashboards
# Verify data quality metrics
```

---

## 📊 Monitoring & Debugging

### Check Pipeline Status

```bash
# List all Spark applications
kubectl get sparkapplications -n spark-operator

# Describe specific application
kubectl describe sparkapplication my-pipeline-landing -n spark-operator

# Get driver logs
kubectl logs -f my-pipeline-landing-driver -n spark-operator

# Get executor logs
kubectl logs -f my-pipeline-landing-exec-1 -n spark-operator
```

### Access Spark UI

```bash
# Port forward to Spark UI
kubectl port-forward svc/my-pipeline-landing-ui-svc 4040:4040 -n spark-operator

# Open browser
open http://localhost:4040
```

### Common Issues

**Out of Memory:**
```yaml
# Increase memory in PROJECT.yaml or K8s manifest
resources:
  transform:
    driver: { cpu: "2", memory: "8Gi" }  # Increase
    executors: { count: 5, cpu: "4", memory: "16Gi" }  # Increase
```

**Slow Performance:**
```python
# Check partition count
df.rdd.getNumPartitions()

# Repartition if needed
df = df.repartition(200)

# Use broadcast for small tables
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(small_df), "key")
```

**Data Quality Failures:**
```python
# Check quality report
report = checker.run_all_checks(df, config)
print(report["details"])

# Filter bad records
good_df = df.filter(quality_condition)
bad_df = df.filter(~quality_condition)
```

---

## 📚 Key Documentation

- **Strategy**: `docs/data-platform/data-pipeline-strategy.md` - Architecture patterns
- **Project Separation**: `docs/data-platform/project-separation-strategy.md` - Organization
- **Quick Reference**: `docs/data-platform/PROJECT-QUICK-REF.md` - Common tasks
- **Examples**: `docs/data-platform/pipelines.md` - Pipeline examples

---

## ⚠️ Critical Reminders

1. **Follow project structure** - Use template, complete PROJECT.yaml
2. **Test thoroughly** - Unit, integration, test data generators
3. **Use common libraries** - Don't reinvent connectors/transforms
4. **Environment progression** - Dev → Staging → Production
5. **Monitor after deployment** - Check logs, Spark UI, Grafana
6. **Document everything** - README, architecture, runbook
7. **Encrypt secrets** - Use SOPS for config/secrets.yaml

---

[← Back to AGENTS.md](../../AGENTS.md) | [Infrastructure Track →](../infrastructure/agent-guide.md)
