# Datacluster - AI Coding Agent Instructions

## Quick Navigation

This repository contains two distinct tracks:

- **🏗️ [Infrastructure Track](./copilot-instructions-infrastructure.md)** - Platform engineering, Kubernetes, Terraform
- **📊 [Data Platform Track](./copilot-instructions-data.md)** - Data pipelines, Spark jobs, analytics

**Choose the appropriate track based on your work context.**

---

## 🎯 Core Principles (All Work)

### 1. GitOps Deployment
- **Infrastructure changes**: Edit manifests in `infrastructure/`, commit, Flux auto-reconciles
- **Data pipelines**: Edit in `data-platform/projects/`, build Docker image, deploy K8s manifests
- **Avoid imperative commands**: Use `kubectl apply` only for debugging/testing
- **Track changes**: All production changes through Git

### 2. Encryption Requirements (CRITICAL)

**ALWAYS encrypt before committing:**
- `talos/cluster.yaml` (cluster config, IPs, tokens)
- `terraform-v2/*.tfvars` (Hetzner API token, credentials)
- `infrastructure/storage/s3-secret.yaml` (S3 credentials)
- Any file with passwords, keys, IP addresses, or tokens

**Workflow:**
```bash
# Generate age key (first time only - backup securely!)
age-keygen -o age.key

# Encrypt files
sops --encrypt --in-place talos/cluster.yaml
sops --encrypt terraform.tfvars > terraform.tfvars.enc

# Edit encrypted files
export SOPS_AGE_KEY_FILE=/projects/dev/datacluster/age.key
sops talos/cluster.yaml  # Decrypts on-the-fly

# Pre-commit check
grep -q "sops:" file || echo "ERROR: Not encrypted!"
```

**Never commit:**
- `age.key` (encryption key - keep offline backup)
- `terraform.tfvars` (unencrypted - always use `.enc` version)
- `config/secrets.yaml` (unencrypted secrets)
- Any file with plaintext credentials

See `docs/infrastructure/encryption.md` for complete guide.

### 3. Repository Structure

```
datacluster/
├── infrastructure/              # 🏗️ Platform (Terraform, K8s, monitoring)
│   ├── monitoring/             # Prometheus, Grafana
│   ├── spark-operator/         # Spark Operator deployment
│   └── storage/                # CSI drivers, S3 secrets
│
├── data-platform/              # 📊 Data pipelines (your analytics code)
│   ├── common/                 # Reusable libraries
│   └── projects/               # Independent pipeline projects
│       ├── user_analytics/     # Self-contained project
│       └── event_streaming/    # Self-contained project
│
├── terraform-v2/               # Hetzner infrastructure as code
├── talos/                      # Talos OS configuration
├── clusters/                   # Flux GitOps definitions
├── docs/
│   ├── infrastructure/         # Platform docs
│   └── data-platform/          # Data pipeline docs
└── scripts/                    # Helper scripts
```

### 4. Standard Tooling

**Infrastructure:**
- `terraform` - Infrastructure as code
- `talosctl` - Talos OS management
- `kubectl` - Kubernetes control
- `flux` - GitOps reconciliation
- `sops` - Secret encryption
- `helm` - Package management

**Data Platform:**
- `spark-submit` - Local Spark testing
- `pytest` - Testing framework
- `docker` - Container builds
- `kubectl` - K8s deployment
- `kustomize` - Environment-specific configs

**Common:**
- `sops` - **Always** for secret management
- `git` - Version control
- `make` / `just` - Task automation (recommended)

### 5. Working with Secrets

**Creating secrets:**
```bash
# 1. Start from example
cp config/secrets.yaml.example config/secrets.yaml

# 2. Fill in real values
vim config/secrets.yaml

# 3. Encrypt
sops --encrypt config/secrets.yaml > config/secrets.yaml.enc

# 4. Commit only encrypted version
git add config/secrets.yaml.enc

# 5. Add to .gitignore
echo "config/secrets.yaml" >> .gitignore
```

**Using secrets in Terraform:**
```bash
export SOPS_AGE_KEY_FILE=/projects/dev/datacluster/age.key
cd terraform-v2
sops -d terraform.tfvars.enc > terraform.tfvars
terraform apply
rm terraform.tfvars  # Always cleanup!
```

### 6. Cluster Access

**Standard configuration locations:**
```bash
# Kubernetes
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config
kubectl get nodes

# Talos
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
talosctl -n <CONTROL_PLANE_PUBLIC_IP> version
```

### 7. Testing Before Production

**Infrastructure:**
```bash
# Terraform: Always plan first
terraform plan -out=upgrade.tfplan
# Review carefully
terraform apply upgrade.tfplan

# Kubernetes: Dry-run
kubectl apply --dry-run=server -f manifest.yaml
```

**Data Pipelines:**
```bash
# Run tests
cd data-platform/projects/my-pipeline/
pytest tests/

# Test locally
spark-submit src/landing.py --config config/environments/dev.yaml

# Deploy to dev first, then staging, then production
kubectl apply -k k8s/overlays/dev/
```

---

## 🚀 Quick Start by Task

---

## 🚀 Quick Start by Task

### Task: Deploy Infrastructure Change
→ See [Infrastructure Track](./copilot-instructions-infrastructure.md)

### Task: Create New Data Pipeline
→ See [Data Platform Track](./copilot-instructions-data.md)

### Task: Add Monitoring Dashboard
→ Infrastructure Track (Grafana in `infrastructure/monitoring/`)

### Task: Scale Spark Resources
→ Data Platform Track (edit `PROJECT.yaml` or K8s manifests)

---

## 📚 Essential Documentation

### Infrastructure
- `docs/infrastructure/architecture.md` - System architecture
- `docs/infrastructure/encryption.md` - SOPS encryption guide
- `docs/infrastructure/hetzner.md` - Hetzner provisioning
- `docs/infrastructure/talos.md` - Talos OS operations
- `docs/infrastructure/monitoring.md` - Monitoring setup

### Data Platform
- `docs/data-platform/project-separation-strategy.md` - Project organization
- `docs/data-platform/PROJECT-QUICK-REF.md` - Quick reference
- `docs/data-platform/data-pipeline-strategy.md` - Architecture strategy

---

## 🔧 Recommended Tooling Improvements

See detailed recommendations in this file below, including:
1. Task Automation with `just` or `make`
2. Pre-commit hooks for validation
3. Direnv for environment management
4. VS Code extensions
5. Project documentation generator
6. Health check scripts

[View full recommendations below](#tooling-recommendations)

---

**Next Steps**: Choose your track and dive in!
- 🏗️ [Infrastructure Track](./copilot-instructions-infrastructure.md)
- 📊 [Data Platform Track](./copilot-instructions-data.md)
