# Documentation Structure

This documentation is organized into two main tracks:

## 🏗️ Infrastructure Documentation

**Location**: `docs/infrastructure/`

Platform engineering, Kubernetes cluster, Terraform infrastructure:

- **[architecture.md](infrastructure/architecture.md)** - System architecture, component overview, cost breakdown
- **[hetzner.md](infrastructure/hetzner.md)** - Hetzner Cloud provisioning, networking setup
- **[talos.md](infrastructure/talos.md)** - Talos OS operations, configuration, troubleshooting
- **[monitoring.md](infrastructure/monitoring.md)** - Prometheus, Grafana, metrics, alerts
- **[encryption.md](infrastructure/encryption.md)** - SOPS encryption setup, key management, rotation
- **[upgrade-guide.md](infrastructure/upgrade-guide.md)** - Kubernetes and Talos version upgrades

**Agent Instructions**: See `../.github/copilot-instructions-infrastructure.md`

---

## 📊 Data Platform Documentation

**Location**: `docs/data-platform/`

Data pipeline development, Spark jobs, analytics:

- **[data-pipeline-strategy.md](data-platform/data-pipeline-strategy.md)** - Overall architecture strategy, storage separation
- **[project-separation-strategy.md](data-platform/project-separation-strategy.md)** - Project organization, mono/multi-repo strategies
- **[PROJECT-QUICK-REF.md](data-platform/PROJECT-QUICK-REF.md)** - Quick reference for working with projects
- **[PROJECT-VISUAL-GUIDE.md](data-platform/PROJECT-VISUAL-GUIDE.md)** - Visual diagrams and flowcharts
- **[pipelines.md](data-platform/pipelines.md)** - Pipeline examples and patterns
- **[pipeline-testing.md](data-platform/pipeline-testing.md)** - Testing strategies

**Agent Instructions**: See `../.github/copilot-instructions-data.md`

---

## 🚀 Getting Started

### For Infrastructure Work:
1. Read [Infrastructure Agent Instructions](../.github/copilot-instructions-infrastructure.md)
2. Review [architecture.md](infrastructure/architecture.md)
3. Set up encryption: [encryption.md](infrastructure/encryption.md)

### For Data Platform Work:
1. Read [Data Platform Agent Instructions](../.github/copilot-instructions-data.md)
2. Review [project-separation-strategy.md](data-platform/project-separation-strategy.md)
3. Check out examples in `../data-platform/projects/`

### Common Instructions:
See [Main Agent Instructions](../.github/copilot-instructions.md) for:
- GitOps deployment principles
- Encryption requirements
- Standard tooling
- Testing practices
- Recommended tooling improvements

---

## 📖 Archive

Older documentation versions are kept in `archive/` for reference only.
