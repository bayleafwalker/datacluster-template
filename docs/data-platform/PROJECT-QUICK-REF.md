# Project Separation - Quick Reference

## 🎯 What is a "Project"?

A **project** is a self-contained folder containing everything for one data pipeline:
- ✅ All configuration in one place
- ✅ Complete documentation
- ✅ Tests and test data generators
- ✅ Kubernetes deployment manifests
- ✅ Can be maintained separately or in a team repository

## 📁 Pick This Folder to Work On

```
data-platform/projects/user-analytics/  👈 THIS is your project
├── PROJECT.yaml                        👈 All metadata in one file
├── config/                             👈 All configuration centralized
├── docs/                               👈 All documentation here
├── src/                                Code
├── tests/                              Tests
├── k8s/                                Kubernetes
└── scripts/                            Automation
```

## 🚀 Quick Commands

### List All Projects
```bash
./scripts/list-projects.sh
```

### Create New Project
```bash
# Copy template
cp -r data-platform/projects/_template data-platform/projects/my-pipeline

# Edit metadata
vim data-platform/projects/my-pipeline/PROJECT.yaml

# Configure
vim data-platform/projects/my-pipeline/config/pipeline.yaml
```

### Import External Project
```bash
./scripts/import-project.sh https://github.com/company/fraud-detection
```

### Export Project to Separate Repo
```bash
./scripts/export-project.sh user-analytics https://github.com/company/user-analytics.git
```

### Work on a Project
```bash
cd data-platform/projects/user-analytics/

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run locally
spark-submit src/landing.py --config config/environments/dev.yaml

# Deploy
kubectl apply -k k8s/overlays/prod/
```

## 📋 PROJECT.yaml - The Single Source of Truth

Every project has ONE file with ALL metadata:

```yaml
name: "user-analytics"
version: "1.2.0"
description: "What this pipeline does"

owner:
  team: "data-engineering"
  slack: "#team-channel"

dependencies:
  data_platform_common: "^0.5.0"
  python: ">=3.9"

resources:
  landing:
    driver: { cpu: "1", memory: "2Gi" }
    executors: { count: 3, cpu: "2", memory: "4Gi" }

schedule:
  landing: "*/15 * * * *"    # Every 15 min
  transform: "0 */1 * * *"   # Hourly

storage:
  landing: "s3://datacluster-data/landing/user-events"
  curated: "s3://datacluster-data/curated/user-analytics"

monitoring:
  grafana_dashboard: "user-analytics-dashboard"
  alerts:
    - name: "high-failure-rate"
      threshold: 0.1
      severity: "critical"

tags: ["analytics", "user-behavior", "critical"]
status: "production"
```

## 📂 Configuration Structure

All project configuration in `config/` directory:

```
config/
├── pipeline.yaml              # Main pipeline config
├── spark.yaml                 # Spark tuning
├── storage.yaml               # S3 buckets, paths
├── secrets.yaml.example       # Secret templates (never commit real secrets!)
└── environments/
    ├── dev.yaml              # Development overrides
    ├── staging.yaml          # Staging overrides
    └── prod.yaml             # Production config
```

**Secrets management:**
```bash
# Create secrets from template
cp config/secrets.yaml.example config/secrets.yaml
# Fill in real values
vim config/secrets.yaml
# Encrypt
sops --encrypt config/secrets.yaml > config/secrets.yaml.enc
# Commit only encrypted version
git add config/secrets.yaml.enc
```

## 📚 Documentation Structure

All project docs in `docs/` directory:

```
docs/
├── README.md                  # Project overview
├── architecture.md            # Design, data flow
├── runbook.md                 # Operations (alerts, recovery)
├── development.md             # Developer setup
├── deployment.md              # Deployment guide
├── data-dictionary.md         # Field descriptions
└── diagrams/                  # Architecture diagrams
```

## 🏢 Multi-Team Scenarios

### Scenario 1: Single Monorepo (Small Team)

```
datacluster/
└── data-platform/
    └── projects/
        ├── user-analytics/      # Team A
        ├── sales-etl/           # Team A
        └── fraud-detection/     # Team B
```

**Pros:** Simple, easy discovery  
**Cons:** All teams in one repo

### Scenario 2: Separate Team Repos (Multiple Teams)

```
datacluster/                    # Platform team
└── data-platform/common/       # Shared libraries

analytics-pipelines/            # Analytics team
├── user-analytics/
└── customer-360/

fraud-pipelines/                # Fraud team
├── fraud-detection/
└── risk-scoring/
```

**Pros:** Team autonomy, independent deployments  
**Cons:** Need to manage dependencies

### Scenario 3: Hybrid (Flexible)

```
datacluster/
└── data-platform/
    └── projects/
        ├── standard-etl/       # Shared templates
        └── basic-ingestion/    # Common patterns

team-a-private-repo/
└── advanced-ml-pipeline/       # Team-specific, complex
```

**Pros:** Shared basics + team flexibility  
**Cons:** More complex to manage

## 🔄 Workflows

### Monorepo Development

```bash
# 1. Create project
cd data-platform/projects/
cp -r _template/ my-pipeline/

# 2. Develop
cd my-pipeline/
vim src/landing.py
pytest tests/

# 3. Build shared image (includes all projects)
cd ../../
docker build -t datacluster-data:1.0.0 .

# 4. Deploy
kubectl apply -k projects/my-pipeline/k8s/overlays/prod/
```

### Separate Repo Development

```bash
# 1. Clone project repo
git clone https://github.com/company/my-pipeline
cd my-pipeline/

# 2. Install dependencies
pip install data-platform-common

# 3. Develop
vim src/landing.py
pytest tests/

# 4. Build project-specific image
docker build -t my-pipeline:1.0.0 .

# 5. Deploy
kubectl apply -k k8s/overlays/prod/
```

## 🛠️ Helper Scripts

| Script | Purpose |
|--------|---------|
| `scripts/list-projects.sh` | List all projects with metadata |
| `scripts/import-project.sh` | Import external project into monorepo |
| `scripts/export-project.sh` | Export project to separate repository |
| `scripts/deploy-pipelines.sh` | Deploy specific pipeline to cluster |

## 📊 Project Status Values

- **development**: Under active development
- **staging**: Testing in staging environment
- **production**: Live in production
- **deprecated**: Scheduled for removal

## 🏷️ Common Tags

Use for discovery and categorization:

- **Domain**: `analytics`, `fraud`, `customer`, `financial`
- **Type**: `batch`, `streaming`, `real-time`, `hybrid`
- **Priority**: `critical`, `high`, `medium`, `low`
- **Data**: `pii`, `confidential`, `internal`, `public`

## 🎨 Standard Project Structure

```
my-pipeline/
├── PROJECT.yaml              ⭐ Single source of truth
├── README.md                 📖 Overview
├── CHANGELOG.md              📝 Version history
│
├── config/                   ⚙️ All configuration centralized
│   ├── pipeline.yaml
│   ├── spark.yaml
│   ├── storage.yaml
│   ├── secrets.yaml.example
│   └── environments/
│       ├── dev.yaml
│       ├── staging.yaml
│       └── prod.yaml
│
├── schemas/                  📋 Data schemas
│   └── v1/
│       ├── landing.avsc
│       └── curated.avsc
│
├── src/                      💻 Source code
│   ├── landing.py
│   ├── transform.py
│   └── integration.py
│
├── tests/                    🧪 Testing
│   ├── unit/
│   ├── integration/
│   ├── generators/          # Test data generators
│   └── fixtures/            # Sample data
│
├── k8s/                      ☸️ Kubernetes
│   ├── base/
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── prod/
│
├── docs/                     📚 Documentation
│   ├── README.md
│   ├── architecture.md
│   ├── runbook.md
│   └── diagrams/
│
└── scripts/                  🔧 Automation
    ├── deploy.sh
    ├── test-local.sh
    └── generate-test-data.sh
```

## 🔐 Secrets Best Practices

1. **Never commit secrets**: Use `.gitignore`
2. **Use templates**: Commit `secrets.yaml.example`
3. **Encrypt with SOPS**: `sops --encrypt secrets.yaml`
4. **Inject at runtime**: Use K8s Secrets or environment variables

```bash
# Good workflow
cp config/secrets.yaml.example config/secrets.yaml
vim config/secrets.yaml  # Fill real values
sops --encrypt config/secrets.yaml > config/secrets.yaml.enc
git add config/secrets.yaml.enc  # Only commit encrypted
echo "config/secrets.yaml" >> .gitignore
```

## 📈 Version Management

### Monorepo Tagging

```bash
# Tag specific project
git tag -a project/user-analytics/v1.2.0 -m "Release 1.2.0"
git push origin project/user-analytics/v1.2.0
```

### Separate Repo Tagging

```bash
# Standard semantic versioning
git tag -a v1.2.0 -m "Release 1.2.0"
git push origin v1.2.0
```

## 🚦 Project Lifecycle

```
Development → Staging → Production → Maintenance → Deprecated → Archived
     ↓           ↓           ↓            ↓            ↓           ↓
   Testing    Integration  Monitoring   Minimal     Sunset    Removed
              Testing      Alerts       Changes     Plan
```

## 📞 Getting Help

- **Documentation**: See `docs/project-separation-strategy.md`
- **Platform Team**: Platform-specific questions
- **Data Team**: Pipeline-specific questions
- **Slack**: #data-platform for discussions

---

**Quick Tip**: The `PROJECT.yaml` file is your single source of truth. Keep it updated!
