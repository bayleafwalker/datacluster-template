# Hetzner Cloud Deployment

This guide covers Hetzner-specific setup including custom Talos image building with Packer and Terraform cluster deployment.

---

## Current Infrastructure

```
Hetzner Cloud (hel1-dc2 datacenter)
├── Servers
│   ├── control-plane-1: CX23 (2 vCPU, 4GB RAM, 40GB disk) @ 10.0.1.101
│   └── worker-1: CX33 (4 vCPU, 8GB RAM, 80GB disk) @ 10.0.1.201
├── Private Network: 10.0.0.0/16 (datacluster)
│   └── Subnet: 10.0.1.0/24 (nodes)
├── Firewall: datacluster (allows K8s API, Talos API, Cilium health)
├── Placement Groups: 2 (spread control-plane and workers across DCs)
├── Primary IPs: 2 static IPv4 addresses
└── Custom Image: Talos v1.11.5 with Tailscale extension (via Packer)
```

**Current versions:**
- **Talos OS**: v1.11.5
- **Kubernetes**: v1.34.1
- **Cilium CNI**: v1.18.3

**Cost: €11.27/month** (€10.01 servers + €1.26 public IPv4s)

---

## Overview

The deployment process has two phases:

1. **Packer** - Build custom Talos images with system extensions (Tailscale)
2. **Terraform** - Deploy Hetzner infrastructure and bootstrap Kubernetes cluster

This approach provides:
- **Custom OS images** with Tailscale VPN baked in
- **Immutable infrastructure** (recreate rather than patch)
- **Version control** of both image builds and cluster config
- **Reproducible deployments** from Git

---

## Phase 1: Build Custom Talos Images with Packer

### Why Custom Images?

Stock Talos images don't include system extensions. We need Tailscale for secure VPN access, so we build custom images using [Talos Image Factory](https://factory.talos.dev/).

### Prerequisites

```bash
# Install Packer
brew install packer  # macOS
# Or download from https://www.packer.io/downloads

# Install Hetzner CLI
brew install hcloud  # macOS
# Or download from https://github.com/hetznercloud/cli/releases

# Set Hetzner API token
export HCLOUD_TOKEN=<your-hetzner-api-token>
```

### Generate Schematic ID

Schematic defines which extensions to include:

```bash
cd _packer

# Post schematic.yaml to Image Factory
curl -X POST --data-binary @schematic.yaml \
  https://factory.talos.dev/schematics

# Returns schematic ID (example):
# {"id":"4a0d65c669d46663f377e7161e50cfd570c401f26fd9e7bda34a0216b6f1922b"}
```

**schematic.yaml contents:**
```yaml
customization:
  systemExtensions:
    officialExtensions:
      - siderolabs/tailscale
```

### Configure Packer

Edit `_packer/hcloud.auto.pkrvars.hcl`:

```hcl
talos_version    = "v1.11.5"
image_url_x86    = "https://factory.talos.dev/image/4a0d65c669d46663f377e7161e50cfd570c401f26fd9e7bda34a0216b6f1922b/v1.11.5/hcloud-amd64.raw.xz"
server_location  = "hel1"  # or fsn1, nbg1
```

**Important:** Schematic IDs are version-specific. When upgrading Talos, regenerate schematic and verify URL exists:

```bash
curl -I "https://factory.talos.dev/image/<SCHEMATIC_ID>/v1.11.5/hcloud-amd64.raw.xz"
# Should return: HTTP/2 200
```

### Build Image

```bash
cd _packer
export HCLOUD_TOKEN=<your-token>
./create.sh
```

**Build process (~9 minutes):**
1. Creates temporary CX22 server in rescue mode
2. Downloads Talos image from Image Factory
3. Writes image to `/dev/sda` with `dd`
4. Creates Hetzner snapshot with labels (os=talos, version=v1.11.5, extensions=tailscale)
5. Deletes temporary server

**Output:**
```
Build 'talos-x86' finished after 8 minutes 42 seconds.
==> Wait completed after 8 minutes 42 seconds
==> Builds finished. The artifacts of successful builds are:
--> talos-x86: A snapshot was created: 'Talos Linux v1.11.5 x86 with Tailscale' (ID: 337659046) in region 'hel1'
```

**Verify:**
```bash
hcloud image list --selector os=talos
# ID: 337659046, Description: Talos Linux v1.11.5 x86 with Tailscale
```

### Packer Troubleshooting

**404 errors during image download:**
- Schematic ID doesn't exist for Talos version
- Solution: Regenerate schematic with `curl -X POST`

**Snapshot creation timeout:**
- Hetzner API rate limit or temporary outage
- Solution: Wait 5 minutes and retry

**Server type unavailable:**
- CX22 not available in selected datacenter
- Solution: Use CX23 or another available server type

See `_packer/README.md` for complete troubleshooting guide.

---

## Phase 2: Deploy Cluster with Terraform

### Prerequisites

```bash
# Install Terraform
brew install terraform  # macOS
# Or download from https://developer.hashicorp.com/terraform/downloads

# Install SOPS and age for secrets
brew install sops age  # macOS

# Generate age key (first time only)
age-keygen -o ../age.key
# BACKUP THIS KEY SECURELY!
```

### Configure Terraform

```bash
cd terraform-v2

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required variables:**
```hcl
# Hetzner API token (Read & Write permissions)
hcloud_token = "<your-hetzner-api-token>"

# Snapshot ID from Packer build
talos_image_id = 337659046

# Component versions
talos_version      = "v1.11.5"
kubernetes_version = "v1.34.1"
cilium_version     = "v1.18.3"

# Infrastructure
server_location            = "hel1"  # Must match Packer location
control_plane_server_type  = "cx23"  # 2 vCPU, 4GB RAM, €3.75/mo
control_plane_runs_workloads = true  # Cost optimization

# Worker nodes
worker_nodes = [
  {
    name = "worker-1"
    type = "cx33"  # 4 vCPU, 8GB RAM, €6.26/mo
  }
]

# Network configuration
network_cidr     = "10.0.0.0/16"
node_cidr        = "10.0.1.0/24"
pod_cidr         = "10.0.16.0/20"
service_cidr     = "10.0.8.0/21"

# Talos configuration
cluster_name     = "datacluster"
cluster_endpoint = "https://kube.cluster.local:6443"

# Tailscale (optional)
tailscale = {
  enabled = true
}
```

### Encrypt Secrets

**CRITICAL:** Never commit unencrypted `terraform.tfvars`!

```bash
export SOPS_AGE_KEY_FILE=../age.key
sops --encrypt terraform.tfvars > terraform.tfvars.enc
rm terraform.tfvars
```

### Deploy Infrastructure

```bash
# Decrypt secrets
export SOPS_AGE_KEY_FILE=../age.key
sops -d terraform.tfvars.enc > terraform.tfvars

# Initialize Terraform
terraform init

# Review plan (38 resources to create)
terraform plan

# Deploy cluster (~8-10 minutes)
terraform apply

# Cleanup decrypted file
rm terraform.tfvars
```

**What Terraform creates:**
1. **Network** (hcloud_network + hcloud_network_subnet)
2. **Firewall** (hcloud_firewall with 2 rules)
3. **Placement Groups** (2, for control-plane and workers)
4. **SSH Key** (hcloud_ssh_key, auto-generated)
5. **Servers** (control-plane-1, worker-1 with Talos image)
6. **Primary IPs** (2 static IPv4 addresses)
7. **Talos Bootstrap** (talos_machine_secrets, talos_machine_configuration_apply, talos_machine_bootstrap)
8. **Cilium CNI** (talos_cluster_kubeconfig, helm_release)

### Extract Kubeconfig

```bash
# Save kubeconfig and talosconfig
terraform output -raw kubeconfig > kubeconfig
terraform output -raw talosconfig > talosconfig

export KUBECONFIG=$PWD/kubeconfig
export TALOSCONFIG=$PWD/talosconfig

# Verify cluster
kubectl get nodes -o wide
# control-plane-1   Ready    control-plane   5m   v1.34.1   10.0.1.101   <CONTROL_PLANE_PUBLIC_IP>
# worker-1          Ready    <none>          4m   v1.34.1   10.0.1.201   <WORKER_PUBLIC_IP>
```

---

## Hetzner-Specific Features

### Server Types

**Available types** (hel1 datacenter):
- **CX23**: 2 vCPU, 4GB RAM, 40GB disk, €3.75/mo (control-plane)
- **CX33**: 4 vCPU, 8GB RAM, 80GB disk, €6.26/mo (worker)
- **CX43**: 8 vCPU, 16GB RAM, 160GB disk, €12.16/mo (large worker)

Scaling: Edit `worker_nodes` in `terraform.tfvars.enc`, run `terraform apply`.

### Private Networking

- **Network**: 10.0.0.0/16 (RFC1918 private)
- **Nodes**: 10.0.1.0/24 (control-plane: .101, workers: .201+)
- **Pods**: 10.0.16.0/20 (Cilium IPAM)
- **Services**: 10.0.8.0/21 (Kubernetes ClusterIPs)

Nodes communicate via private network only. Public IPs used for:
- Kubernetes API access (port 6443)
- Talos API access (port 50000)
- Cilium health checks

### Firewall Rules

```yaml
Inbound:
  - Port 6443/tcp (Kubernetes API) from any
  - Port 50000/tcp (Talos API) from any
  - Port 4240/tcp (Cilium health) from private network
  - ICMP (ping) from any

Outbound:
  - All traffic allowed
```

Apply to all servers via `hcloud_firewall_attachment`.

### Placement Groups

Ensures high availability by spreading nodes across physical hardware:
- **control-plane** placement group (spread type)
- **worker** placement group (spread type)

Prevents single-point-of-failure at datacenter level.

### Volumes (Optional)

Not currently used, but available for:
- Persistent storage (PVCs)
- Spark checkpoints
- Streaming job state

**Create with Terraform:**
```hcl
resource "hcloud_volume" "spark_data" {
  name     = "spark-data"
  size     = 100  # GB
  location = "hel1"
  format   = "ext4"
}

resource "hcloud_volume_attachment" "spark_data" {
  volume_id = hcloud_volume.spark_data.id
  server_id = hcloud_server.worker[0].id
}
```

**Cost:** €0.05/GB/month (100GB = €5/month)

### Object Storage (S3-compatible)

For large datasets, use Hetzner Object Storage:

1. Create bucket at Console → Object Storage
   - Region: hel1
   - Name: `datacluster-spark`

2. Store credentials as Kubernetes Secret:
```bash
kubectl create secret generic s3-credentials \
  --from-literal=access-key=<key> \
  --from-literal=secret-key=<secret> \
  --namespace=spark-operator
```

3. Encrypt secret YAML:
```bash
kubectl get secret s3-credentials -n spark-operator -o yaml > infrastructure/storage/s3-secret.yaml
export SOPS_AGE_KEY_FILE=../age.key
sops --encrypt --in-place infrastructure/storage/s3-secret.yaml
```

4. Reference in SparkApplications:
```yaml
spec:
  hadoopConf:
    fs.s3a.endpoint: https://hel1.your-objectstorage.hetzner.com
    fs.s3a.access.key: <from-secret>
    fs.s3a.secret.key: <from-secret>
```

**Cost:** €0.023/GB/month + €0.005/1000 requests (100GB = €2.30/month)

---

## Cost Management

### Current Monthly Costs

| Component | Cost |
|-----------|------|
| CX23 control-plane | €3.75 |
| CX33 worker | €6.26 |
| Public IPv4 (×2) | €1.26 |
| Network | Free |
| Firewall | Free |
| **Total** | **€11.27** |

### Pause Cluster (Keep Configuration)

```bash
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops -d terraform.tfvars.enc > terraform.tfvars

# Destroy only servers
terraform destroy -target=hcloud_server.control_plane -target=hcloud_server.worker
rm terraform.tfvars

# Cost: €0/month (network and firewall are free)
```

**Resume:**
```bash
terraform apply
# Servers recreate with same IPs (primary IPs persist)
```

### Full Destruction

```bash
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops -d terraform.tfvars.enc > terraform.tfvars

terraform destroy  # Removes everything
rm terraform.tfvars

# Delete Packer image (optional)
hcloud image delete <SNAPSHOT_ID>
```

---

## Monitoring Costs

### Via Hetzner Console

1. Go to https://console.hetzner.cloud/
2. Select project
3. Click "Billing" → "Current Period"

### Via CLI

```bash
# List all resources with costs
hcloud server list -o json | jq -r '.[] | "\(.name): \(.server_type.prices[] | select(.location=="hel1").price_monthly.gross)"'

# Total monthly estimate
hcloud server list -o json | jq '[.[] | .server_type.prices[] | select(.location=="hel1").price_monthly.net | tonumber] | add'
```

---

## Scaling

### Add Worker Nodes

```bash
# Edit terraform.tfvars
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops terraform.tfvars.enc

# Add to worker_nodes:
# worker_nodes = [
#   { name = "worker-1", type = "cx33" },
#   { name = "worker-2", type = "cx33" }  # New worker
# ]

# Apply
sops -d terraform.tfvars.enc > terraform.tfvars
terraform apply
rm terraform.tfvars

# Verify
kubectl get nodes
```

**Cost:** +€6.26/month per CX33 worker

### Upgrade Server Types

```bash
# Stop workloads first
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data

# Edit terraform.tfvars
sops terraform.tfvars.enc
# Change: worker_nodes[0].type = "cx43"

# Apply (recreates server)
sops -d terraform.tfvars.enc > terraform.tfvars
terraform apply
rm terraform.tfvars

# Verify
kubectl get nodes
# worker-1 should show more CPU/RAM
```

---

## Troubleshooting

### Can't access Kubernetes API

**Symptoms:** `kubectl get nodes` times out

**Diagnosis:**
```bash
# Check firewall rules
hcloud firewall describe datacluster

# Check server public IPs
hcloud server list

# Test API endpoint
curl -k https://<control-plane-ip>:6443/healthz
# Should return 403 (Forbidden) - means API is reachable
```

**Fix:**
- Verify KUBECONFIG points to correct file
- Ensure firewall allows port 6443 from your IP
- Check if control-plane server is running

### Talos not bootstrapping

**Symptoms:** `terraform apply` hangs at "Waiting for Talos bootstrap"

**Diagnosis:**
```bash
# Check Talos logs
talosctl -n <control-plane-ip> logs

# Check Talos services
talosctl -n <control-plane-ip> services

# Check etcd status
talosctl -n <control-plane-ip> etcd members
```

**Fix:**
- Verify Talos image ID is correct in terraform.tfvars
- Check if custom image exists: `hcloud image describe <ID>`
- Ensure network connectivity between nodes

### Cilium pods not starting

**Symptoms:** `kubectl get pods -n kube-system` shows cilium pods in CrashLoopBackOff

**Diagnosis:**
```bash
kubectl logs -n kube-system ds/cilium
kubectl describe pods -n kube-system -l k8s-app=cilium
```

**Fix:**
- Verify Cilium version compatibility with Kubernetes
- Check firewall allows Cilium health checks (port 4240)
- Ensure private network is configured correctly

### Packer snapshot missing after cluster creation

**Symptoms:** Terraform fails with "Image not found"

**Diagnosis:**
```bash
hcloud image list --selector os=talos
# Should show at least one Talos image
```

**Fix:**
- Rebuild Packer image: `cd _packer && ./create.sh`
- Update terraform.tfvars with new snapshot ID
- Keep old snapshots as rollback insurance

---

## Migration from Old Setup

If migrating from old infrastructure (different Talos version, no Packer, etc.):

1. **Backup data** (if any persistent volumes exist)
2. **Destroy old cluster**: `terraform destroy` (in old directory)
3. **Build Packer images** (this guide, Phase 1)
4. **Deploy new cluster** (this guide, Phase 2)
5. **Restore data** from backup

**No in-place upgrade path** - we use immutable infrastructure philosophy.

---

## Additional Resources

- **[Hetzner Cloud Docs](https://docs.hetzner.com/cloud/)** - Official documentation
- **[Talos Hetzner Guide](https://www.talos.dev/latest/talos-guides/install/cloud-platforms/hetzner/)** - Talos-specific setup
- **[Packer Hetzner Plugin](https://github.com/hetznercloud/packer-plugin-hcloud)** - Plugin documentation
- **[_packer/README.md](../_packer/README.md)** - Detailed Packer guide
- **[VERSION-UPDATES.md](../VERSION-UPDATES.md)** - Upgrade procedures
