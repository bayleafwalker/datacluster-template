# Project Separation Strategy

## Overview

This document defines how to organize data pipelines as **independent projects** that can be:
- Maintained in separate repositories
- Owned by different teams
- Deployed independently
- Versioned independently
- Tested in isolation

## Core Concepts

### What is a "Project"?

A **project** is a self-contained unit representing:
- **One data pipeline** (e.g., user analytics, fraud detection)
- **One data source** (e.g., Salesforce integration, MySQL CDC)
- **One test system** (e.g., staging data generator, QA simulator)
- **One business domain** (e.g., customer 360, inventory management)

### Project Independence

Each project must be:
1. **Self-documenting**: Complete documentation in project directory
2. **Self-configuring**: All configs in one place (no scattered settings)
3. **Self-testing**: Tests, test data generators, and fixtures included
4. **Self-deploying**: Kubernetes manifests and CI/CD pipelines included
5. **Dependency-explicit**: Clear declaration of common library versions

---

## Directory Structure

### Option 1: Monorepo (Current - Recommended for Small Teams)

```
datacluster/
├── infrastructure/           # Platform (owned by platform team)
│   ├── monitoring/
│   ├── spark-operator/
│   └── storage/
│
├── data-platform/
│   ├── common/              # Shared libraries (platform team)
│   │   ├── connectors/
│   │   ├── transforms/
│   │   └── storage/
│   │
│   └── projects/            # 👈 NEW: Rename from "pipelines"
│       ├── user-analytics/         # Project 1
│       ├── sales-etl/              # Project 2
│       ├── fraud-detection/        # Project 3
│       ├── kafka-cdc-postgres/     # Project 4 (source)
│       ├── test-data-generator/    # Project 5 (test system)
│       └── _template/              # Project template
│
└── docs/                    # Platform documentation
```

### Option 2: Multi-Repo (Recommended for Multiple Teams)

**Main Platform Repository** (`datacluster`):
```
datacluster/
├── infrastructure/
├── data-platform/
│   ├── common/              # Versioned package
│   └── _template/           # Project template
├── docs/
└── scripts/
    └── import-project.sh    # Import external projects
```

**External Project Repositories** (e.g., `analytics-pipelines`):
```
analytics-pipelines/          # Separate Git repository
├── user-analytics/           # Project 1
├── customer-360/             # Project 2
├── product-recommendations/  # Project 3
├── .github/
│   └── workflows/
│       └── deploy.yaml       # CI/CD for these projects
├── pyproject.toml            # Dependency on data-platform-common
├── README.md
└── CONTRIBUTING.md
```

**Team-Specific Repository** (e.g., `fraud-team-pipelines`):
```
fraud-team-pipelines/
├── fraud-detection/
├── risk-scoring/
├── anomaly-detection/
└── shared/                   # Team-specific utilities
    └── fraud_models/
```

---

## Standard Project Structure

Every project follows this structure (whether in monorepo or separate repo):

```
project-name/                 # 👈 Pick this folder to work on entire project
├── PROJECT.yaml              # 👈 Project metadata (NEW)
├── README.md                 # Project overview
├── CHANGELOG.md              # Version history
│
├── config/                   # 👈 ALL configuration centralized
│   ├── pipeline.yaml         # Pipeline-specific config
│   ├── spark.yaml            # Spark tuning parameters
│   ├── storage.yaml          # S3 buckets, paths, retention
│   ├── secrets.yaml.example  # Secret templates (never commit real secrets)
│   └── environments/
│       ├── dev.yaml          # Development overrides
│       ├── staging.yaml      # Staging overrides
│       └── prod.yaml         # Production config
│
├── schemas/                  # Data schemas
│   ├── v1/
│   │   ├── landing.avsc      # Input schema
│   │   └── curated.avsc      # Output schema
│   └── v2/                   # Schema evolution
│       └── landing.avsc
│
├── src/                      # Source code
│   ├── __init__.py
│   ├── landing.py            # Stage 1: Ingestion
│   ├── transform.py          # Stage 2: Processing
│   ├── integration.py        # Stage 3: Publishing
│   └── utils/                # Project-specific utilities
│       ├── __init__.py
│       ├── validators.py
│       └── transformers.py
│
├── tests/                    # Testing
│   ├── unit/
│   │   ├── test_landing.py
│   │   ├── test_transform.py
│   │   └── test_integration.py
│   ├── integration/
│   │   └── test_end_to_end.py
│   ├── generators/
│   │   ├── test_data.py      # Generate test data
│   │   ├── edge_cases.py     # Edge case scenarios
│   │   └── load_testing.py   # Performance test data
│   └── fixtures/
│       ├── sample_input.parquet
│       └── expected_output.parquet
│
├── k8s/                      # Kubernetes deployment
│   ├── base/
│   │   ├── landing.yaml      # SparkApplication for landing
│   │   ├── transform.yaml    # SparkApplication for transform
│   │   ├── integration.yaml  # SparkApplication for integration
│   │   ├── workflow.yaml     # Argo Workflow (optional)
│   │   └── kustomization.yaml
│   └── overlays/
│       ├── dev/
│       │   ├── kustomization.yaml
│       │   └── patches.yaml
│       ├── staging/
│       └── prod/
│
├── docs/                     # 👈 Project documentation centralized
│   ├── README.md             # Detailed project overview
│   ├── architecture.md       # Design decisions, data flow
│   ├── runbook.md            # Operations guide (alerts, recovery)
│   ├── development.md        # Developer setup, local testing
│   ├── deployment.md         # Deployment guide
│   ├── data-dictionary.md    # Field descriptions, business rules
│   ├── dependencies.md       # External dependencies, SLAs
│   └── diagrams/
│       ├── data-flow.png
│       └── architecture.png
│
├── scripts/                  # Project-specific automation
│   ├── deploy.sh             # Deploy to cluster
│   ├── test-local.sh         # Run locally
│   ├── generate-test-data.sh # Generate test data
│   └── backfill.sh           # Historical data processing
│
├── .github/                  # CI/CD (if separate repo)
│   └── workflows/
│       ├── test.yaml
│       ├── build.yaml
│       └── deploy.yaml
│
├── Dockerfile                # Project-specific image (optional)
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Poetry/modern Python packaging
└── .gitignore

```

---

## PROJECT.yaml - Project Metadata

Every project includes a `PROJECT.yaml` file at the root:

```yaml
# Project metadata
name: user-analytics
version: "1.2.0"
description: "User behavior analytics pipeline processing clickstream data"

# Ownership
owner:
  team: "data-engineering"
  slack: "#data-eng-alerts"
  email: "data-eng@company.com"
  on_call: "https://pagerduty.com/data-eng"

# Dependencies
dependencies:
  data_platform_common: "^0.5.0"  # SemVer
  python: ">=3.9,<3.12"
  spark: "3.5.0"
  delta_lake: "3.0.0"

# External systems
integrations:
  sources:
    - type: "kafka"
      topic: "user-events"
      cluster: "production-kafka"
      schema_registry: "https://schema-registry.prod"
    - type: "s3"
      bucket: "s3://landing/user-events"
      
  destinations:
    - type: "delta"
      path: "s3://curated/user-analytics"
    - type: "kafka"
      topic: "analytics-results"

# Resource requirements
resources:
  landing:
    driver: { cpu: "1", memory: "2Gi" }
    executors: { count: 3, cpu: "2", memory: "4Gi" }
  transform:
    driver: { cpu: "2", memory: "4Gi" }
    executors: { count: 5, cpu: "4", memory: "8Gi" }

# Scheduling
schedule:
  landing: "*/15 * * * *"        # Every 15 minutes
  transform: "0 */1 * * *"       # Hourly
  integration: "0 2 * * *"       # Daily at 2 AM

# SLAs
sla:
  latency: "30m"                 # Data available within 30 minutes
  availability: "99.9%"
  data_quality_threshold: 0.95   # 95% pass quality checks

# Monitoring
monitoring:
  prometheus: true
  grafana_dashboard: "user-analytics-dashboard"
  alerts:
    - name: "high-failure-rate"
      threshold: 0.1
      severity: "critical"

# Storage
storage:
  landing:
    path: "s3://datacluster-data/landing/user-events"
    retention: "7d"
    format: "avro"
  curated:
    path: "s3://datacluster-data/curated/user-analytics"
    retention: "permanent"
    format: "delta"
  checkpoints:
    path: "s3://datacluster-data/checkpoints/user-analytics"
    retention: "30d"

# Testing
testing:
  unit_tests: true
  integration_tests: true
  test_data_generator: "tests/generators/test_data.py"
  sample_data_path: "tests/fixtures/"

# Documentation
documentation:
  main: "docs/README.md"
  architecture: "docs/architecture.md"
  runbook: "docs/runbook.md"
  confluence: "https://wiki.company.com/user-analytics"

# Tags
tags:
  - "analytics"
  - "user-behavior"
  - "real-time"
  - "critical"

# Status
status: "production"  # development | staging | production | deprecated

# Repository (if separate repo)
repository:
  url: "https://github.com/company/analytics-pipelines"
  path: "user-analytics"

# Last updated
updated_at: "2025-12-02"
updated_by: "jane.doe@company.com"
```

---

## Multi-Repository Strategy

### Repository Organization

**Option A: By Team**
```
├── datacluster (platform team)
├── analytics-pipelines (analytics team)
├── fraud-pipelines (fraud team)
└── integration-pipelines (data integration team)
```

**Option B: By Domain**
```
├── datacluster (platform)
├── customer-domain-pipelines
├── product-domain-pipelines
└── financial-domain-pipelines
```

**Option C: Hybrid**
```
├── datacluster (platform + shared projects)
├── team-a-private-pipelines (private team repo)
└── external-vendor-integration (third-party)
```

### Shared Common Library

Publish `data-platform-common` as a Python package:

**Option 1: Private PyPI**
```bash
pip install data-platform-common==0.5.0
```

**Option 2: Git Submodule**
```bash
git submodule add https://github.com/company/datacluster common
```

**Option 3: Git Dependency (pyproject.toml)**
```toml
[tool.poetry.dependencies]
data-platform-common = { git = "https://github.com/company/datacluster.git", subdirectory = "data-platform/common", tag = "v0.5.0" }
```

### Project Import/Export

**Import external project into monorepo:**
```bash
# scripts/import-project.sh
#!/bin/bash
PROJECT_REPO=$1
PROJECT_NAME=$(basename $PROJECT_REPO .git)

cd data-platform/projects/
git clone $PROJECT_REPO $PROJECT_NAME
cd $PROJECT_NAME

# Validate structure
if [ ! -f "PROJECT.yaml" ]; then
  echo "❌ Invalid project: missing PROJECT.yaml"
  exit 1
fi

# Build and deploy
docker build -t datacluster-$PROJECT_NAME:latest .
kubectl apply -k k8s/overlays/prod/
```

**Export project from monorepo:**
```bash
# scripts/export-project.sh
#!/bin/bash
PROJECT_NAME=$1
TARGET_REPO=$2

# Create new repository with project
git subtree split --prefix=data-platform/projects/$PROJECT_NAME -b $PROJECT_NAME-export
git remote add $PROJECT_NAME-remote $TARGET_REPO
git push $PROJECT_NAME-remote $PROJECT_NAME-export:main
```

---

## Project Lifecycle

### 1. Project Creation

**From template (monorepo):**
```bash
cd data-platform/projects/
cp -r _template/ my-new-project/
cd my-new-project/

# Customize PROJECT.yaml
vim PROJECT.yaml

# Initialize configuration
cp config/secrets.yaml.example config/secrets.yaml.enc
sops --encrypt config/secrets.yaml.enc
```

**New separate repository:**
```bash
# Create from template
gh repo create company/my-new-project --template company/datacluster-project-template

cd my-new-project/

# Install common libraries
poetry add data-platform-common@^0.5.0

# Develop
vim src/landing.py
pytest tests/
```

### 2. Development Workflow

```bash
# Local testing
cd data-platform/projects/user-analytics/
poetry install
pytest tests/unit/
pytest tests/integration/

# Generate test data
python tests/generators/test_data.py --output /tmp/test-data/

# Run locally
spark-submit \
  --master local[*] \
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
  src/landing.py \
  --config config/environments/dev.yaml
```

### 3. Deployment

**Monorepo:**
```bash
cd data-platform/projects/user-analytics/

# Build shared image (includes all projects)
cd ../../
docker build -t datacluster-data:1.2.0 .
docker push ghcr.io/company/datacluster-data:1.2.0

# Deploy specific project
kubectl apply -k projects/user-analytics/k8s/overlays/prod/
```

**Separate repo:**
```bash
# Build project-specific image
docker build -t user-analytics:1.2.0 .
docker push ghcr.io/company/user-analytics:1.2.0

# Deploy
kubectl apply -k k8s/overlays/prod/
```

### 4. Version Management

**Monorepo versioning:**
```
data-platform v0.5.0 (common libraries)
├── user-analytics v1.2.0
├── sales-etl v2.1.0
└── fraud-detection v1.0.0
```

**Tag format:** `project/user-analytics/v1.2.0`

**Separate repo versioning:**
```
user-analytics v1.2.0 (repo)
└── depends on data-platform-common ^0.5.0
```

---

## Team Collaboration Models

### Model 1: Platform Team + Data Teams (Recommended)

**Platform Team** (owns `datacluster` repo):
- Maintains infrastructure
- Develops common libraries
- Provides project template
- Reviews project deployments

**Data Teams** (own separate project repos):
- Develop pipelines in their repos
- Use common libraries as dependency
- Deploy independently
- Own project monitoring

**Workflow:**
```
Platform Team                    Data Team
     │                              │
     ├─ Release common v0.6.0       │
     │                              │
     │                              ├─ Update dependency to v0.6.0
     │                              ├─ Develop user-analytics v1.3.0
     │                              ├─ Run tests
     │                              │
     │                              ├─ PR to datacluster (optional)
     │◄─────────────────────────────┤ Request review/deploy
     │                              │
     ├─ Review project structure    │
     ├─ Approve deployment          │
     │────────────────────────────► │
     │                              ├─ Deploy to production
```

### Model 2: Full Independence

Each team maintains everything independently:
```
Team A Repo                     Team B Repo
├── common-fork/                ├── common-fork/
├── user-analytics/             ├── fraud-detection/
└── customer-360/               └── risk-scoring/
```

**Pros:** Complete autonomy  
**Cons:** Code duplication, divergence

### Model 3: Federated (Hybrid)

Core projects in main repo, advanced projects in team repos:
```
datacluster/
├── infrastructure/
├── common/
└── projects/
    ├── basic-etl/              # Simple, shared
    └── standard-ingestion/     # Shared templates

team-a-repo/
└── projects/
    ├── advanced-ml-pipeline/   # Complex, private
    └── proprietary-algorithm/  # IP protection
```

---

## Configuration Management

### Centralized Config Structure

All project configuration in `config/` directory:

```yaml
# config/pipeline.yaml (main config)
pipeline:
  name: "user-analytics"
  type: "batch"  # batch | streaming | hybrid
  
  stages:
    landing:
      enabled: true
      parallelism: 10
      timeout: "30m"
    
    transform:
      enabled: true
      parallelism: 20
      timeout: "2h"
    
    integration:
      enabled: true
      parallelism: 5
      timeout: "15m"

sources:
  - name: "kafka-user-events"
    type: "kafka"
    config_ref: "kafka.yaml"
  
  - name: "s3-historical"
    type: "s3"
    config_ref: "storage.yaml"

destinations:
  - name: "delta-curated"
    type: "delta"
    config_ref: "storage.yaml"
  
  - name: "kafka-analytics-results"
    type: "kafka"
    config_ref: "kafka.yaml"

quality_checks:
  enabled: true
  threshold: 0.95
  rules:
    - type: "null_check"
      columns: ["user_id", "timestamp"]
    - type: "duplicate_check"
      key_columns: ["user_id", "event_id"]
    - type: "freshness"
      max_age: "1h"

monitoring:
  enabled: true
  metrics:
    - "rows_processed"
    - "processing_time"
    - "quality_score"
  alerts:
    - name: "high-failure-rate"
      condition: "failure_rate > 0.1"
      severity: "critical"
```

### Environment-Specific Overrides

```yaml
# config/environments/prod.yaml
pipeline:
  stages:
    landing:
      parallelism: 50      # Override: more parallelism in prod
    transform:
      parallelism: 100
      timeout: "4h"

resources:
  landing:
    executors:
      count: 10            # Override: more executors
      memory: "8Gi"

storage:
  landing:
    path: "s3://prod-landing/user-events"  # Different bucket
  curated:
    path: "s3://prod-curated/user-analytics"
```

### Secrets Management

```yaml
# config/secrets.yaml.example (template, committed)
kafka:
  bootstrap_servers: "KAFKA_BOOTSTRAP_SERVERS"
  sasl_username: "KAFKA_USERNAME"
  sasl_password: "KAFKA_PASSWORD"

s3:
  access_key: "S3_ACCESS_KEY"
  secret_key: "S3_SECRET_KEY"

database:
  jdbc_url: "JDBC_URL"
  username: "DB_USERNAME"
  password: "DB_PASSWORD"
```

```bash
# Actual secrets (NEVER committed)
cp config/secrets.yaml.example config/secrets.yaml
# Fill in real values
sops --encrypt config/secrets.yaml > config/secrets.yaml.enc
# Commit only encrypted version
git add config/secrets.yaml.enc
```

---

## Project Discovery & Catalog

### Project Registry

Create a project registry for discovery:

```yaml
# data-platform/PROJECT-REGISTRY.yaml
projects:
  - name: "user-analytics"
    path: "projects/user-analytics"
    repository: "https://github.com/company/datacluster"
    owner: "data-engineering"
    status: "production"
    version: "1.2.0"
    tags: ["analytics", "user-behavior", "real-time"]
  
  - name: "fraud-detection"
    path: "projects/fraud-detection"
    repository: "https://github.com/company/fraud-pipelines"
    owner: "fraud-team"
    status: "production"
    version: "2.1.0"
    tags: ["ml", "fraud", "critical"]
  
  - name: "test-data-generator"
    path: "projects/test-data-generator"
    repository: "https://github.com/company/datacluster"
    owner: "platform-team"
    status: "development"
    version: "0.5.0"
    tags: ["testing", "qa"]
```

### CLI Tool for Project Management

```bash
# List all projects
datactl project list

# Get project info
datactl project info user-analytics

# Create new project
datactl project create my-pipeline --template batch

# Deploy project
datactl project deploy user-analytics --env prod

# Test project
datactl project test user-analytics

# Generate project documentation
datactl project docs user-analytics --output docs/
```

---

## Migration Path

### Phase 1: Reorganize Current Structure ✅ (Week 1)

```bash
# Rename pipelines → projects
mv data-platform/pipelines data-platform/projects

# Add PROJECT.yaml to existing projects
for project in data-platform/projects/*/; do
  cp data-platform/_template/PROJECT.yaml $project/
  # Customize PROJECT.yaml for each
done

# Reorganize configs
for project in data-platform/projects/*/; do
  mkdir -p $project/config
  # Move any scattered configs to config/
done

# Enhance documentation
for project in data-platform/projects/*/; do
  mkdir -p $project/docs
  # Ensure README, architecture, runbook exist
done
```

### Phase 2: Add Multi-Repo Support (Week 2-3)

```bash
# Publish common library
cd data-platform/common/
poetry build
poetry publish --repository private-pypi

# Create project template repo
gh repo create company/datacluster-project-template --public
cd datacluster-project-template/
cp -r ../data-platform/_template/* .
# Add GitHub Actions, README
git push

# Document import/export procedures
# Create scripts/import-project.sh
# Create scripts/export-project.sh
```

### Phase 3: Enable Team Repositories (Week 4)

```bash
# Team A creates their repo from template
gh repo create company/analytics-pipelines --template company/datacluster-project-template

# Add projects
cd analytics-pipelines/
mkdir -p user-analytics/ customer-360/

# Set up CI/CD
# Configure dependencies on common library

# Deploy independently
kubectl apply -k user-analytics/k8s/overlays/prod/
```

---

## Best Practices

### ✅ DO

1. **Complete PROJECT.yaml** for every project
2. **Centralize all config** in `config/` directory
3. **Document thoroughly** in `docs/` subdirectory
4. **Version independently** using semantic versioning
5. **Test in isolation** with project-specific test data
6. **Use environment overlays** (dev/staging/prod)
7. **Declare dependencies explicitly** in requirements.txt or pyproject.toml
8. **Tag releases** properly (`project/name/vX.Y.Z`)

### ❌ DON'T

1. **Don't scatter config** across multiple locations
2. **Don't share mutable state** between projects
3. **Don't hard-code** environment-specific values
4. **Don't commit secrets** (use SOPS encryption)
5. **Don't skip documentation** (future you will thank you)
6. **Don't couple projects** with direct imports
7. **Don't use latest** dependency versions in production

---

## Tooling & Automation

### Recommended Tools

**Project Management:**
- `datactl` (custom CLI) - project lifecycle management
- `kubectl kustomize` - environment-specific deployments
- `poetry` or `pipenv` - Python dependency management

**CI/CD:**
- GitHub Actions / GitLab CI
- Argo CD - GitOps deployment
- Flux CD - continuous reconciliation

**Testing:**
- `pytest` - unit and integration tests
- `great_expectations` - data quality validation
- `tox` - multi-environment testing

**Documentation:**
- `mkdocs` - beautiful project documentation
- `sphinx` - API documentation
- `mermaid` - diagrams as code

### Sample GitHub Actions Workflow

```yaml
# .github/workflows/deploy-project.yaml
name: Deploy Project

on:
  push:
    branches: [main]
    paths:
      - 'user-analytics/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          cd user-analytics/
          poetry install
          poetry run pytest tests/
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          cd user-analytics/
          docker build -t ghcr.io/${{ github.repository }}/user-analytics:${{ github.sha }} .
          docker push ghcr.io/${{ github.repository }}/user-analytics:${{ github.sha }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Kubernetes
        run: |
          cd user-analytics/k8s/overlays/prod/
          kustomize edit set image user-analytics=ghcr.io/${{ github.repository }}/user-analytics:${{ github.sha }}
          kubectl apply -k .
```

---

## Summary

### Key Decisions

| Aspect | Monorepo | Multi-Repo |
|--------|----------|------------|
| **Team size** | Small (1-5 people) | Large (5+ teams) |
| **Coordination** | Easy | Requires process |
| **Versioning** | Shared tags | Independent |
| **CI/CD** | Single pipeline | Per-repo pipelines |
| **Discovery** | Easy (one place) | Needs catalog |
| **Governance** | Centralized | Federated |

### Next Steps

1. ✅ **Rename** `data-platform/pipelines` → `data-platform/projects`
2. ✅ **Add PROJECT.yaml** to all existing projects
3. ✅ **Centralize config** in `config/` directories
4. ✅ **Enhance docs** in `docs/` subdirectories
5. ⏳ **Publish common library** as Python package
6. ⏳ **Create project template** repository
7. ⏳ **Build datactl CLI** for project management
8. ⏳ **Set up CI/CD** workflows
9. ⏳ **Create project registry** and catalog
10. ⏳ **Document team workflows** and handoff procedures

---

**Status**: 🚧 Planning complete, ready for implementation  
**Owner**: Platform Team  
**Timeline**: 4 weeks  
**Impact**: Enables multi-team collaboration, improves maintainability
