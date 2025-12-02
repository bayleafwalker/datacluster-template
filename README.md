# Datacluster

> **🎯 This is a PUBLIC TEMPLATE repository**  
> This repository contains **NO REAL SECRETS** - all sensitive data has been removed or replaced with placeholders.  
> Fork this repository and follow the Getting Started guide to deploy your own cluster.

---

# Datacluster

Cost-optimized Apache Spark platform on Hetzner Cloud (€11/month).

**Stack:**
- **Kubernetes**: Talos OS v1.11.5 + Kubernetes v1.34.1
- **Infrastructure**: Terraform + Hetzner Cloud (CX23 control-plane + CX33 worker)
- **Networking**: Cilium CNI v1.18.3, Tailscale VPN
- **Data Processing**: Apache Spark 3.5+ with Spark Operator
- **Storage**: Hetzner Volumes (CSI) + Object Storage (S3)
- **GitOps**: FluxCD for declarative infrastructure
- **Monitoring**: Prometheus + Grafana
- **Secrets**: SOPS-encrypted with age

---

## Getting Started

### Pre-Flight Checklist

Before you begin, ensure you have completed these steps:

- [ ] **Hetzner Cloud account** created with payment method
- [ ] **Hetzner project** created (e.g., "datacluster-prod")
- [ ] **Hetzner API token** generated (Read & Write permissions) and saved
- [ ] **GitHub account** with a fork of this repository
- [ ] **GitHub Personal Access Token** created (`repo` + `write:packages` scopes) and saved
- [ ] **Tools installed**: terraform, kubectl, talosctl, sops, age, hcloud, packer, flux
- [ ] **Git configured** with your name and email
- [ ] **Budget approved**: ~€11/month for infrastructure

**Estimated time**: 45-60 minutes for full setup

---

### Prerequisites

**Required Tools:**
```bash
# macOS
brew install terraform kubectl talosctl sops age hcloud packer

# Linux (Ubuntu/Debian)
sudo apt update && sudo apt install -y curl wget git
# Install each tool from official releases:
# - terraform: https://developer.hashicorp.com/terraform/downloads
# - kubectl: https://kubernetes.io/docs/tasks/tools/
# - talosctl: https://www.talos.dev/latest/introduction/getting-started/
# - sops: https://github.com/getsops/sops/releases
# - age: https://github.com/FiloSottile/age/releases
# - hcloud: https://github.com/hetznercloud/cli/releases
# - packer: https://www.packer.io/downloads
```

**Required Accounts:**

1. **Hetzner Cloud** (REQUIRED):
   - Create account: https://console.hetzner.cloud/
   - Create a new project (e.g., "datacluster-prod")
   - Generate API token: Console → Security → API Tokens
     - Name: "terraform-datacluster"
     - Permissions: **Read & Write** (required for Terraform)
     - Save token securely - shown only once!

2. **GitHub** (REQUIRED for Flux GitOps):
   - Create Personal Access Token: https://github.com/settings/tokens/new
   - Select scopes: `repo` (full control), `write:packages` (for container registry)
   - Name: "flux-datacluster"
   - Expiration: 90 days or longer
   - Save token securely - shown only once!

3. **Tailscale** (OPTIONAL but recommended):
   - Sign up: https://tailscale.com/
   - Generate auth key: https://login.tailscale.com/admin/settings/keys
   - Select: Reusable, Ephemeral
   - For secure VPN access to cluster

**Cost Estimate:** ~€11/month (€10 servers + €1.26 public IPs)

---

### Step 1: Fork Repository and Setup Encryption

**Fork the repository first** (required for Flux GitOps):

1. Go to https://github.com/<YOUR-GITHUB-USERNAME>/datacluster
2. Click "Fork" → Create fork under your account
3. Clone YOUR fork (not the original):

```bash
# Clone your fork
git clone https://github.com/<YOUR-USERNAME>/datacluster.git
cd datacluster

# Set up Git identity
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

**Generate encryption key:**

```bash
# Generate age encryption key (BACKUP THIS SECURELY!)
age-keygen -o age.key

# Output example:
# Public key: age1abc123...
# AGE-SECRET-KEY-1ABC123...

# Extract public key
cat age.key | grep "public key:"
# Copy the age1... string (starts with age1)
```

**Update .sops.yaml with YOUR public key:**

```bash
# Edit .sops.yaml
nano .sops.yaml

# Replace EVERY occurrence of the age key with YOUR public key
# Look for lines like:
#   age: >
#     age1ulmhqhp2t2x9pte5n4e06sc809ucful63k0u30v2np40d2sa53pq2wuv0l
# Replace with YOUR age1... key from above

# Verify replacement
grep "age1" .sops.yaml
# Should show YOUR key, not the example key

# Commit the updated .sops.yaml
git add .sops.yaml
git commit -m "chore: update SOPS age key"
git push
```

**CRITICAL:** 
- Store `age.key` securely (password manager, USB drive, encrypted backup)
- NEVER commit `age.key` to Git (it's in .gitignore)
- Losing this key means you cannot decrypt ANY secrets
- Make multiple backups in different locations

---

### Step 2: Build Custom Talos Images with Packer

Talos OS requires custom images with system extensions (Tailscale VPN). Build these with Packer:

```bash
cd _packer

# Set Hetzner API token (from Prerequisites step)
export HCLOUD_TOKEN="<your-hetzner-api-token>"

# Verify token works and select correct project
hcloud project list
hcloud context create datacluster
hcloud context use datacluster
# Or set active project: https://console.hetzner.cloud/projects

# Generate schematic ID for Tailscale extension
curl -X POST --data-binary @schematic.yaml \
  https://factory.talos.dev/schematics
# Returns: {"id":"4a0d65c669d46663f377e7161e50cfd570c401f26fd9e7bda34a0216b6f1922b"}

# Update hcloud.auto.pkrvars.hcl with schematic ID
nano hcloud.auto.pkrvars.hcl
# Set:
# - talos_version = "v1.11.5"
# - image_url_x86 = "https://factory.talos.dev/image/<SCHEMATIC_ID>/v1.11.5/hcloud-amd64.raw.xz"
# - server_location = "hel1" (or fsn1/nbg1)

# Build image (~9 minutes)
./create.sh
# Creates Hetzner snapshot with ID (e.g., 337659046)

# Verify
hcloud image list --selector os=talos
# Should show: Talos Linux v1.11.5 x86 with Tailscale
```

**Why Packer?** Stock Talos images don't include Tailscale. Packer builds custom images with system extensions, creating Hetzner snapshots for Terraform deployment.

See `_packer/README.md` for troubleshooting and advanced options.

---

### Step 3: Configure Terraform

```bash
cd ../terraform-v2

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
# Required fields:
# - hcloud_token: Your Hetzner API token
# - talos_image_id: Snapshot ID from Packer (e.g., 337659046)
# - talos_version: "v1.11.5"
# - kubernetes_version: "v1.34.1"
# - cilium_version: "v1.18.3"
# - server_location: "hel1" (match Packer location)

# ENCRYPT before committing (REQUIRED!)
export SOPS_AGE_KEY_FILE=../age.key
sops --encrypt terraform.tfvars > terraform.tfvars.enc
rm terraform.tfvars  # Never commit unencrypted secrets!
```

**Terraform Configuration:**
- `control_plane_server_type = "cx23"` (2 vCPU, 4GB RAM, €3.75/mo)
- `worker_nodes[0].type = "cx33"` (4 vCPU, 8GB RAM, €6.26/mo)
- `control_plane_runs_workloads = true` (cost optimization)
- Network: 10.0.0.0/16 private, 10.0.1.0/24 nodes, 10.0.16.0/20 pods, 10.0.8.0/21 services

---

### Step 4: Deploy Cluster

```bash
# Decrypt and apply Terraform (from terraform-v2/)
export SOPS_AGE_KEY_FILE=../age.key
sops -d terraform.tfvars.enc > terraform.tfvars

terraform init
terraform plan   # Review 38 resources to create
terraform apply  # Deploys in ~8-10 minutes

# Cleanup decrypted file
rm terraform.tfvars

# Extract kubeconfig and talosconfig
terraform output -raw kubeconfig > kubeconfig
terraform output -raw talosconfig > talosconfig

export KUBECONFIG=$PWD/kubeconfig
export TALOSCONFIG=$PWD/talosconfig
```

**What gets created:**
- 2 Hetzner servers (control-plane-1, worker-1)
- Private network (10.0.0.0/16) with subnet
- Firewall (allows Kubernetes API + Talos API + Cilium health checks)
- 2 placement groups (spread across datacenters)
- 2 primary IPs (static IPv4 addresses)
- SSH key for server management

---

### Step 5: Verify Cluster

```bash
# Check nodes
kubectl get nodes -o wide
# Both should show: Ready, v1.34.1, Talos (v1.11.5)

# Check Cilium CNI
kubectl get pods -n kube-system -l k8s-app=cilium
kubectl exec -n kube-system ds/cilium -- cilium-dbg status

# Check all system pods
kubectl get pods -n kube-system
# Should see: cilium, coredns, cloud-controller-managers (Hetzner + Talos)

# Test cluster
kubectl run test-pod --image=nginx --restart=Never
kubectl get pods
kubectl delete pod test-pod
```

**Access cluster:**
- **Via Tailscale VPN**: Connect control-plane to Tailscale network, access via internal IP
- **Via public IP**: Control-plane at public IPv4 (from Terraform output), but only Kubernetes/Talos APIs exposed

---

### Step 6: Bootstrap Flux GitOps

**Required: GitHub Personal Access Token** (from Prerequisites)
- Create at: https://github.com/settings/tokens/new
- Scopes: `repo` (full control), `write:packages`
- Save token - you'll enter it below

```bash
cd ../

# Set standard kubeconfig location
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config
cp terraform-v2/kubeconfig clusters/.kube/config

# Bootstrap Flux (recommended for GitOps)
# You'll be prompted for GitHub token - paste it when asked
flux bootstrap github \
  --owner=<your-github-username> \
  --repository=datacluster \
  --branch=main \
  --path=clusters/hetzner-prod \
  --personal

# Flux will:
# - Install controllers in flux-system namespace
# - Create deploy key for repository access
# - Commit flux-system manifests to Git
# - Auto-reconcile infrastructure/ and pipelines/ directories

# Verify Flux installation
flux check
flux get kustomizations
flux get helmreleases -A

# Watch reconciliation progress
kubectl get pods -n flux-system
kubectl get pods -n storage
kubectl get pods -n spark-operator
kubectl get pods -n monitoring
```

**What Flux deploys:**
- `infrastructure-storage` → Hetzner CSI drivers + S3 credentials
- `infrastructure-spark-operator` → Spark Operator for job orchestration
- `infrastructure-monitoring` → Prometheus + Grafana dashboards
- `pipelines` → Sample Spark jobs

**IMPORTANT - S3 Credentials Setup:**

The S3 secret in `infrastructure/spark-operator/s3-secret.yaml` contains placeholder values. To use Hetzner Object Storage:

1. Create Object Storage in Hetzner Console: https://console.hetzner.cloud/projects → Object Storage
2. Generate S3 credentials (Access Key + Secret Key)
3. Update and encrypt the secret:

```bash
export SOPS_AGE_KEY_FILE=/projects/dev/datacluster/age.key

# Edit the secret
sops infrastructure/spark-operator/s3-secret.yaml

# Update these fields:
#   access-key: "<your-hetzner-s3-access-key>"
#   secret-key: "<your-hetzner-s3-secret-key>"
#   endpoint: "https://fsn1.your-objectstorage.com"  # Your region
#   region: "fsn1"  # Your region

# Save and commit
git add infrastructure/spark-operator/s3-secret.yaml
git commit -m "chore: configure S3 credentials"
git push

# Flux will auto-reconcile the secret
flux reconcile kustomization infrastructure-spark-operator
```

**Troubleshooting Flux:**
```bash
# Check Flux logs
flux logs --level=error --all-namespaces

# Force reconciliation
flux reconcile kustomization flux-system --with-source

# Check specific kustomization
kubectl describe kustomization infrastructure-storage -n flux-system

# Check if kustomizations are stuck
flux get kustomizations
# Expected: All should eventually show READY=True
# Initial reconciliation may take 5-10 minutes
```

**Common Issues:**

1. **S3 secret errors**: Update placeholder credentials (see above)
2. **HelmRelease timeout**: Storage provisioner may take time, wait 10 minutes
3. **Dependency failures**: Check that storage kustomization completes first

**Manual deployment (without Flux):**
```bash
# If not using GitOps, deploy manually
kubectl apply -k infrastructure/storage/
kubectl apply -k infrastructure/spark-operator/
kubectl apply -k infrastructure/monitoring/
```

See `docs/architecture.md` for component details and `docs/monitoring.md` for Grafana setup.

---

## Repository Structure

```
├── _packer/              # Custom Talos image builds
│   ├── schematic.yaml    # Tailscale extension definition
│   ├── hcloud.auto.pkrvars.hcl  # Packer variables
│   ├── talos-hcloud.pkr.hcl     # Packer build definition
│   └── create.sh         # Build automation script
├── terraform-v2/         # Infrastructure as code
│   ├── main.tf           # Hetzner resources + Talos bootstrap
│   ├── variables.tf      # Configuration variables
│   ├── terraform.tfvars.enc  # SOPS-encrypted secrets
│   └── outputs.tf        # Kubeconfig, talosconfig, IPs
├── talos/                # Talos cluster configuration (optional)
│   └── cluster.yaml      # Advanced Talos config (SOPS-encrypted)
├── clusters/             # FluxCD GitOps definitions
│   └── hetzner-prod/     # Production cluster manifests
├── infrastructure/       # Platform components
│   ├── monitoring/       # Prometheus + Grafana
│   ├── spark-operator/   # Spark job orchestration
│   ├── storage/          # Hetzner CSI + S3 credentials
│   └── workflows/        # Argo Workflows (optional)
├── pipelines/            # Spark job definitions
│   └── *.yaml            # SparkApplication CRDs
├── src/                  # PySpark application code
│   ├── batch_job.py      # Example ETL job
│   ├── streaming_job.py  # Example streaming job
│   └── Dockerfile        # Spark image with dependencies
├── docs/                 # Documentation
│   ├── architecture.md   # System design
│   ├── hetzner.md        # Hetzner-specific details
│   ├── talos.md          # Talos configuration guide
│   ├── encryption.md     # SOPS workflow
│   ├── monitoring.md     # Observability setup
│   └── pipelines.md      # Spark job examples
└── age.key.example       # Template for SOPS key
```

---

## Common Tasks

### Access Cluster
```bash
# Use standard locations
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig

kubectl get nodes

# Get control-plane IP
cd terraform-v2
terraform output control_plane_public_ips
# Use IP from output
talosctl -n <CONTROL_PLANE_PUBLIC_IP> version
```

### Run Spark Job
```bash
kubectl apply -f pipelines/example-batch-job.yaml
kubectl get sparkapplications
kubectl logs <spark-driver-pod>
```

### Check Monitoring
```bash
kubectl port-forward -n monitoring svc/grafana 3000:80
# Open http://localhost:3000 (admin/admin)
```

### Update Secrets
```bash
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops terraform.tfvars.enc  # Edit in-place
# Save and commit encrypted file
```

### Destroy Cluster
```bash
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops -d terraform.tfvars.enc > terraform.tfvars
terraform destroy
rm terraform.tfvars
```

---

## Documentation

- **[Getting Started](README.md)** - This guide
- **[VERSION-UPDATES.md](VERSION-UPDATES.md)** - Upgrade procedures
- **[docs/architecture.md](docs/architecture.md)** - System design and components
- **[docs/hetzner.md](docs/hetzner.md)** - Hetzner Cloud setup and Packer workflow
- **[docs/talos.md](docs/talos.md)** - Talos configuration reference
- **[docs/encryption.md](docs/encryption.md)** - SOPS encryption workflow
- **[docs/monitoring.md](docs/monitoring.md)** - Prometheus + Grafana setup
- **[docs/pipelines.md](docs/pipelines.md)** - Spark job examples
- **[_packer/README.md](_packer/README.md)** - Custom image building

---

## Cost Breakdown

| Component | Type | Cost/Month |
|-----------|------|------------|
| Control-plane | CX23 (2 vCPU, 4GB RAM) | €3.75 |
| Worker | CX33 (4 vCPU, 8GB RAM) | €6.26 |
| Public IPv4 | 2 addresses | €1.26 |
| Network | Private network | Free |
| Firewall | Rules | Free |
| **Total** | | **€11.27** |

**Optional costs:**
- Hetzner Volumes: €0.05/GB/month (10GB = €0.50)
- Object Storage: €0.023/GB/month (100GB = €2.30)
- Additional workers: €6.26/month each

**Cost optimization:**
- Pause cluster: `terraform destroy -target=hcloud_server.*` (keeps network, €0/month)
- Resume: `terraform apply` + re-run Packer if image deleted

---

## Troubleshooting

### Packer build fails with 404
Image Factory schematic ID doesn't exist for Talos version. Regenerate:
```bash
curl -X POST --data-binary @_packer/schematic.yaml https://factory.talos.dev/schematics
```

### Nodes not joining cluster
Check Talos logs:
```bash
talosctl -n <node-ip> logs
talosctl -n <node-ip> get members
```

### Can't access cluster
Verify kubeconfig and firewall:
```bash
kubectl cluster-info
hcloud firewall describe datacluster
```

### Cilium pods not ready
Check CNI configuration:
```bash
kubectl logs -n kube-system ds/cilium
kubectl exec -n kube-system ds/cilium -- cilium-dbg status
```

See `docs/troubleshooting.md` for complete troubleshooting guide.

---

## Security Best Practices

1. **NEVER commit unencrypted secrets** - Always encrypt `terraform.tfvars` before `git add`
2. **Backup age.key securely** - Store in password manager, encrypted backup
3. **Use Tailscale VPN** - Avoid exposing cluster on public internet
4. **Enable Hetzner firewall** - Restrict access to Kubernetes API
5. **Rotate credentials regularly** - Update Hetzner API tokens, SOPS keys
6. **Review Terraform plans** - Always run `terraform plan` before `apply`

---

## Next Steps

- Configure Tailscale VPN for secure access
- Deploy monitoring stack (Prometheus + Grafana)
- Set up Hetzner Object Storage for Spark datasets
- Build and push custom Spark Docker images
- Deploy sample Spark pipelines
- Configure FluxCD for GitOps automation

See `docs/monitoring.md` and `docs/pipelines.md` for detailed guides.
