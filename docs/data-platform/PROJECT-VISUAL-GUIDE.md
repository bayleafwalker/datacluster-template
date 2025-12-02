# Project Separation - Visual Guide

## 📦 What is a "Project"?

```
┌─────────────────────────────────────────────────────────────────┐
│                    ONE COMPLETE PROJECT                          │
│  (Everything in one folder - pick this folder to work on it!)   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  📁 data-platform/projects/user-analytics/  👈 Pick this!       │
│  │                                                                │
│  ├── 📄 PROJECT.yaml          ⭐ Single source of truth          │
│  │   • Owner (team, contacts)                                    │
│  │   • Resources (CPU, memory)                                   │
│  │   • Schedule (when it runs)                                   │
│  │   • Monitoring (alerts, dashboards)                           │
│  │   • Storage (where data lives)                                │
│  │   • SLAs (latency, quality)                                   │
│  │                                                                │
│  ├── 📁 config/               ⚙️ All configuration here          │
│  │   ├── pipeline.yaml        (main config)                      │
│  │   ├── spark.yaml           (Spark settings)                   │
│  │   ├── storage.yaml         (S3 buckets)                       │
│  │   ├── secrets.yaml.enc     (encrypted secrets)                │
│  │   └── environments/        (dev/staging/prod overrides)       │
│  │                                                                │
│  ├── 📁 docs/                 📚 All documentation here          │
│  │   ├── README.md            (overview)                         │
│  │   ├── architecture.md      (design, data flow)                │
│  │   ├── runbook.md           (operations, alerts)               │
│  │   └── data-dictionary.md  (field descriptions)                │
│  │                                                                │
│  ├── 📁 src/                  💻 Source code                     │
│  │   ├── landing.py           (stage 1: ingest)                  │
│  │   ├── transform.py         (stage 2: process)                 │
│  │   └── integration.py       (stage 3: publish)                 │
│  │                                                                │
│  ├── 📁 tests/                🧪 Testing                         │
│  │   ├── unit/                (unit tests)                       │
│  │   ├── integration/         (integration tests)                │
│  │   ├── generators/          (test data generators)             │
│  │   └── fixtures/            (sample data)                      │
│  │                                                                │
│  ├── 📁 k8s/                  ☸️ Kubernetes                      │
│  │   ├── base/                (base manifests)                   │
│  │   └── overlays/            (dev/staging/prod)                 │
│  │                                                                │
│  ├── 📁 schemas/              📋 Data schemas                    │
│  │   └── v1/                  (versioned Avro schemas)           │
│  │                                                                │
│  └── 📁 scripts/              🔧 Automation                      │
│      ├── deploy.sh            (deploy to cluster)                │
│      └── test-local.sh        (run locally)                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🏢 Repository Strategies

### Strategy 1: Monorepo (Small Teams)

```
┌─────────────────────────────────────────────────────────────────┐
│                      datacluster (one repo)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  infrastructure/         👈 Platform team manages                │
│  ├── monitoring/                                                  │
│  ├── spark-operator/                                              │
│  └── storage/                                                     │
│                                                                   │
│  data-platform/                                                   │
│  ├── common/            👈 Shared libraries                      │
│  │   ├── connectors/                                              │
│  │   ├── transforms/                                              │
│  │   └── storage/                                                 │
│  │                                                                 │
│  └── projects/          👈 All projects in one place             │
│      ├── user-analytics/      (Team A)                           │
│      ├── sales-etl/           (Team A)                           │
│      ├── fraud-detection/     (Team B)                           │
│      └── event-streaming/     (Team B)                           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

✅ Pros: Simple, easy discovery, shared CI/CD
❌ Cons: All teams in one repo, potential conflicts
```

### Strategy 2: Multi-Repo (Multiple Teams)

```
┌─────────────────────────────────────────────────────────────────┐
│                 datacluster (platform repo)                      │
├─────────────────────────────────────────────────────────────────┤
│  infrastructure/                                                  │
│  data-platform/common/  👈 Published as Python package          │
│  docs/                                                            │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ depends on
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│            analytics-pipelines (Analytics Team)                  │
├─────────────────────────────────────────────────────────────────┤
│  user-analytics/        👈 Independent projects                 │
│  customer-360/                                                    │
│  product-recommendations/                                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              fraud-pipelines (Fraud Team)                        │
├─────────────────────────────────────────────────────────────────┤
│  fraud-detection/       👈 Team autonomy                         │
│  risk-scoring/                                                    │
│  anomaly-detection/                                               │
└─────────────────────────────────────────────────────────────────┘

✅ Pros: Team autonomy, independent deployments, separate versions
❌ Cons: More coordination, need project catalog, dependency management
```

## 🔄 Development Workflows

### Monorepo Workflow

```
Developer                    Monorepo                    Cluster
   │                            │                           │
   ├─ Create project            │                           │
   │  (copy template)           │                           │
   │                            │                           │
   ├─ Edit code ────────────────▶ Commit to main            │
   │  (src/, tests/)            │                           │
   │                            │                           │
   ├─ Push changes ─────────────▶ Shared CI/CD             │
   │                            │  (builds all)             │
   │                            │                           │
   │                            ├─ Build image ─────────────▶ Deploy
   │                            │  (includes all projects)  │
   │                            │                           │
   │                            ├─ Deploy specific ─────────▶ Run
   │                            │  project manifests        │
   │                            │                           │
   └─ Monitor ◀─────────────────┴───────────────────────────┘
      (Grafana, logs)
```

### Multi-Repo Workflow

```
Team A                      Team Repo                  Cluster
   │                            │                           │
   ├─ Clone project repo        │                           │
   │                            │                           │
   ├─ Install common lib ───────▶ pip install               │
   │  (from platform)           │ data-platform-common      │
   │                            │                           │
   ├─ Edit code ────────────────▶ Commit to team repo       │
   │  (independent)             │                           │
   │                            │                           │
   ├─ Push changes ─────────────▶ Team-specific CI/CD      │
   │                            │  (builds only this)       │
   │                            │                           │
   │                            ├─ Build image ─────────────▶ Deploy
   │                            │  (project-specific)       │
   │                            │                           │
   │                            ├─ Deploy ──────────────────▶ Run
   │                            │  (team controls)          │
   │                            │                           │
   └─ Monitor ◀─────────────────┴───────────────────────────┘
      (team's Grafana)
```

## 📊 Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Configuration Layers                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1️⃣  PROJECT.yaml                                                │
│     ┌────────────────────────────────────────────────────┐      │
│     │ Base metadata, defaults                             │      │
│     │ • Owner, team                                       │      │
│     │ • Dependencies                                      │      │
│     │ • Base resources                                    │      │
│     │ • Monitoring config                                 │      │
│     └────────────────────────────────────────────────────┘      │
│                          ↓ merged with                           │
│                                                                   │
│  2️⃣  config/pipeline.yaml                                        │
│     ┌────────────────────────────────────────────────────┐      │
│     │ Pipeline-specific configuration                     │      │
│     │ • Data sources                                      │      │
│     │ • Transformations                                   │      │
│     │ • Quality checks                                    │      │
│     └────────────────────────────────────────────────────┘      │
│                          ↓ merged with                           │
│                                                                   │
│  3️⃣  config/environments/prod.yaml                               │
│     ┌────────────────────────────────────────────────────┐      │
│     │ Environment-specific overrides                      │      │
│     │ • More resources in prod                            │      │
│     │ • Different storage paths                           │      │
│     │ • Production secrets                                │      │
│     └────────────────────────────────────────────────────┘      │
│                          ↓ final config                          │
│                                                                   │
│  🚀 Deployed Configuration                                       │
│     ┌────────────────────────────────────────────────────┐      │
│     │ Final merged configuration used at runtime          │      │
│     └────────────────────────────────────────────────────┘      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Helper Scripts Usage

```
┌─────────────────────────────────────────────────────────────────┐
│                      Project Management                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  List Projects                                                    │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ $ ./scripts/list-projects.sh                          │       │
│  │                                                        │       │
│  │ PROJECT              VERSION    STATUS      TEAM      │       │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │       │
│  │ user-analytics       1.2.0      production  data-eng  │       │
│  │ fraud-detection      2.0.0      production  fraud     │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
│  Import External Project                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ $ ./scripts/import-project.sh \                       │       │
│  │     https://github.com/company/fraud-detection        │       │
│  │                                                        │       │
│  │ ⬇️  Cloning repository...                             │       │
│  │ ✅ Validating project structure...                    │       │
│  │ 📋 Reading project metadata...                        │       │
│  │ ✅ Project imported successfully!                     │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
│  Export Project to Separate Repo                                 │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ $ ./scripts/export-project.sh user-analytics \        │       │
│  │     https://github.com/company/user-analytics.git     │       │
│  │                                                        │       │
│  │ 📦 Exporting project: user-analytics                  │       │
│  │ 📁 Preparing export...                                │       │
│  │ 🚀 Pushing to remote repository...                    │       │
│  │ ✅ Project exported successfully!                     │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Quick Decision Tree

```
                     Starting a new pipeline?
                              │
                              ↓
              ┌───────────────┴───────────────┐
              │                               │
         Small team?                    Multiple teams?
              │                               │
              ↓                               ↓
    Use Monorepo Strategy          Use Multi-Repo Strategy
              │                               │
              ↓                               ↓
   ┌──────────────────────┐       ┌──────────────────────┐
   │ 1. Copy template     │       │ 1. Create new repo   │
   │ 2. Edit PROJECT.yaml │       │ 2. Add common lib    │
   │ 3. Develop in src/   │       │ 3. Copy template     │
   │ 4. Test locally      │       │ 4. Develop & test    │
   │ 5. Deploy to cluster │       │ 5. Team CI/CD        │
   └──────────────────────┘       └──────────────────────┘
```

## 📚 Documentation Locations

```
┌─────────────────────────────────────────────────────────────────┐
│                    Where to Find Things                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Complete Strategy                                                │
│  📄 docs/project-separation-strategy.md                          │
│     • Repository organization (monorepo vs multi-repo)           │
│     • Standard project structure                                 │
│     • PROJECT.yaml specification                                 │
│     • Configuration management                                   │
│     • Team collaboration models                                  │
│     • Migration path                                             │
│                                                                   │
│  Quick Reference                                                  │
│  📄 docs/PROJECT-QUICK-REF.md                                    │
│     • Quick commands                                             │
│     • Common workflows                                           │
│     • Configuration examples                                     │
│     • Best practices                                             │
│                                                                   │
│  Implementation Summary                                           │
│  📄 docs/PROJECT-SEPARATION-SUMMARY.md                           │
│     • What was created                                           │
│     • Key concepts                                               │
│     • Usage examples                                             │
│     • Checklist for new projects                                 │
│                                                                   │
│  Project Template                                                 │
│  📁 data-platform/projects/_template/                            │
│     • PROJECT.yaml template                                      │
│     • Complete directory structure                               │
│     • Example code and configs                                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Getting Started Checklist

```
□ Read project-separation-strategy.md
□ Review PROJECT-QUICK-REF.md
□ Understand your team's strategy (monorepo vs multi-repo)
□ Copy _template/ to create your project
□ Fill out PROJECT.yaml completely
□ Centralize config in config/ directory
□ Write comprehensive docs in docs/
□ Implement stages in src/
□ Create tests in tests/
□ Define K8s manifests in k8s/
□ Test locally
□ Deploy to dev environment
□ Deploy to production
□ Set up monitoring and alerts
```

---

**Remember**: Pick the project folder, and everything you need is there! 📦
