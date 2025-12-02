# Talos and Kubernetes Upgrade Guide

## Overview

This guide covers upgrading Talos OS and Kubernetes versions on the Datacluster. The recommended approach is infrastructure recreation rather than in-place upgrades for major version jumps.

## Current Versions (as of Dec 2, 2025)

- **Talos OS**: v1.11.5
- **Kubernetes**: v1.32.1
- **Cilium CNI**: v1.17.0

## Upgrade Strategy

### Option 1: Infrastructure Recreation (Recommended)

This approach destroys and recreates the entire cluster with new versions. It's faster and cleaner for major version upgrades.

**Pros**:
- Clean slate, no version skew issues
- Faster than incremental upgrades (15-20 minutes total)
- Avoids intermediate version compatibility problems
- Guaranteed consistent state

**Cons**:
- Cluster downtime required (15-20 minutes)
- All workloads must be redeployed
- Ephemeral data is lost

**Use when**:
- Upgrading multiple major versions
- Testing new configurations
- No critical workloads running
- Clean state is desired

### Option 2: In-Place Upgrade (For Minor Versions)

Upgrade running nodes without recreation. Only recommended for minor version bumps (e.g., v1.8.x → v1.8.y or v1.30.x → v1.31.x).

**Pros**:
- Minimal downtime
- Workloads continue running
- Persistent data preserved

**Cons**:
- Can fail with large version jumps
- May require intermediate versions
- Takes longer (30-45 minutes)

**Use when**:
- Single minor version upgrade
- Critical workloads cannot have downtime
- Upgrade path is straightforward

## Prerequisites

Before upgrading:

1. **Backup critical data** (if any):
   ```bash
   # Export any important ConfigMaps, Secrets, etc.
   kubectl get cm,secret -n your-namespace -o yaml > backup.yaml
   ```

2. **Check version compatibility**:
   - Verify [Talos version matrix](https://www.talos.dev/latest/introduction/support-matrix/)
   - Check Kubernetes version support in Talos release notes

3. **Set correct cluster context**:
   ```bash
   export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config
   export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
   ```

4. **Verify current versions**:
   ```bash
   kubectl version
   talosctl version --nodes <control-plane-ip>
   ```

## Procedure: Infrastructure Recreation

### Step 1: Update Terraform Configuration

Edit `terraform-v2/main.tf`:

```hcl
module "talos" {
  # ... other config ...
  
  # Update these versions
  talos_version      = "v1.11.5"      # New Talos version
  kubernetes_version = "v1.32.1"      # New Kubernetes version
  cilium_version     = "v1.17.0"      # New Cilium version
}
```

### Step 2: Delete Existing Infrastructure

```bash
cd /projects/dev/datacluster/terraform-v2

# Decrypt tfvars
export SOPS_AGE_KEY_FILE=../age.key
sops -d terraform.tfvars.enc > terraform.tfvars

# Method A: Via Terraform (recommended)
terraform destroy -auto-approve

# Method B: Manual cleanup (if Terraform state is out of sync)
export HCLOUD_TOKEN=$(grep hcloud_token terraform.tfvars | cut -d'"' -f2)

# Delete servers
hcloud server delete control-plane-1
hcloud server delete worker-1

# Wait for servers to be fully deleted
sleep 15

# Delete network resources
hcloud network delete datacluster
hcloud firewall delete datacluster

# Delete placement groups
hcloud placement-group delete control-plane
hcloud placement-group delete worker

# Delete SSH keys
hcloud ssh-key delete default
hcloud ssh-key delete datacluster-key

# Delete primary IPs (get IDs from: hcloud primary-ip list)
hcloud primary-ip delete <control-plane-ip-id>
hcloud primary-ip delete <worker-ip-id>

# Clean up tfvars
rm terraform.tfvars
```

### Step 3: Create New Infrastructure

```bash
cd /projects/dev/datacluster/terraform-v2

# Decrypt tfvars
export SOPS_AGE_KEY_FILE=../age.key
sops -d terraform.tfvars.enc > terraform.tfvars

# Apply Terraform
terraform apply -auto-approve

# This will:
# 1. Create new servers with Talos v1.11.5
# 2. Bootstrap Kubernetes v1.32.1
# 3. Install Cilium v1.17.0
# 4. Configure Tailscale VPN
# 5. Apply Hetzner Cloud Controller Manager

# Cleanup
rm terraform.tfvars
```

**Expected duration**: 15-20 minutes

### Step 4: Update Kubeconfig

```bash
# Copy new kubeconfig to standard location
cp /projects/dev/datacluster/terraform-v2/kubeconfig \
   /projects/dev/datacluster/clusters/.kube/config

# Verify cluster access
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config
kubectl get nodes

# Expected output:
# NAME              STATUS   ROLES           AGE   VERSION
# control-plane-1   Ready    control-plane   5m    v1.32.1
# worker-1          Ready    <none>          3m    v1.32.1
```

### Step 5: Redeploy Infrastructure

```bash
# Set correct context
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config

# Deploy monitoring stack
kubectl apply -k infrastructure/monitoring/

# Deploy Spark Operator
kubectl apply -k infrastructure/spark-operator/

# Wait for operators to be ready
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=kube-prometheus-stack-operator \
  -n monitoring \
  --timeout=600s

kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=spark-operator \
  -n spark-operator \
  --timeout=600s
```

### Step 6: Verify Upgrade

```bash
# Check versions
kubectl version
kubectl get nodes -o wide

# Check all pods running
kubectl get pods -A

# Test Spark pipeline deployment
kubectl apply -f pipelines/sample-pipelines.yaml
kubectl get sparkapplications -n spark-operator

# Access Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# Open: http://localhost:3000 (admin/admin)
```

## Procedure: In-Place Upgrade (Minor Versions Only)

### Step 1: Upgrade Talos OS

Upgrade control plane first, then workers.

```bash
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
CONTROL_PLANE_IP=<control-plane-public-ip>
WORKER_IP=<worker-public-ip>

# Upgrade control plane
talosctl upgrade \
  --nodes $CONTROL_PLANE_IP \
  --image ghcr.io/siderolabs/installer:v1.9.0 \
  --preserve

# Wait for control plane to come back (5-10 minutes)
talosctl version --nodes $CONTROL_PLANE_IP

# Upgrade worker
talosctl upgrade \
  --nodes $WORKER_IP \
  --image ghcr.io/siderolabs/installer:v1.9.0 \
  --preserve

# Wait for worker to come back
talosctl version --nodes $WORKER_IP
```

### Step 2: Upgrade Kubernetes

```bash
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config

# Upgrade to next minor version (e.g., v1.30.3 → v1.31.0)
talosctl upgrade-k8s \
  --nodes $CONTROL_PLANE_IP \
  --to v1.31.0

# Verify
kubectl get nodes
kubectl version
```

### Step 3: Verify

```bash
# Check all pods healthy
kubectl get pods -A

# Check node conditions
kubectl describe nodes

# Test workload deployment
kubectl run test-nginx --image=nginx --rm -it -- /bin/sh
```

## Troubleshooting

### Upgrade Failed: Version Skew Too Large

**Problem**: `talosctl upgrade` fails with version compatibility error

**Solution**: Use infrastructure recreation instead:
```bash
# Update terraform-v2/main.tf with target versions
# Follow "Infrastructure Recreation" procedure above
```

### Nodes Not Coming Back After Upgrade

**Problem**: Nodes stuck in NotReady state after upgrade

**Solution**:
```bash
# Check Talos logs
talosctl logs --nodes <ip> -f

# Common issues:
# 1. Cilium not ready → Wait 5 more minutes
# 2. kubelet not starting → Check API server connectivity
# 3. Certificate issues → May need to regenerate

# If stuck >15 minutes, recreate infrastructure
```

### Kubeconfig Invalid After Upgrade

**Problem**: `kubectl` commands fail with certificate errors

**Solution**:
```bash
# Regenerate kubeconfig
cd /projects/dev/datacluster/terraform-v2
terraform output -raw kubeconfig > /projects/dev/datacluster/clusters/.kube/config

# Or recreate via talosctl
talosctl kubeconfig --nodes <control-plane-ip> \
  --force \
  ~/.kube/config
```

### Workloads Not Starting After Upgrade

**Problem**: Pods stuck in Pending or ImagePullBackOff

**Solution**:
```bash
# Check node resources
kubectl describe nodes

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Common fixes:
# 1. Resource constraints → Scale down or increase node size
# 2. Missing CRDs → Redeploy operators
# 3. Image pull issues → Check registry credentials
```

## Version History

| Date       | Talos   | Kubernetes | Cilium  | Notes                          |
|------------|---------|------------|---------|--------------------------------|
| 2025-12-02 | v1.11.5 | v1.32.1    | v1.17.0 | Major upgrade via recreation   |
| 2025-12-01 | v1.8.4  | v1.30.3    | v1.16.5 | Initial deployment             |

## Maintenance Schedule

**Recommended upgrade frequency**:
- **Talos OS**: Every 2-3 months (follow stable releases)
- **Kubernetes**: Every 3-4 months (stay within N-2 supported versions)
- **Cilium**: Every 3-6 months (or when Talos recommends)

**When to upgrade**:
- ✅ Security patches released
- ✅ New features needed
- ✅ Staying within vendor support window
- ❌ Cluster is unstable
- ❌ Major workloads running in production
- ❌ Right before critical deadline

## References

- **Talos Documentation**: https://www.talos.dev/latest/
- **Kubernetes Release Notes**: https://kubernetes.io/releases/
- **Cilium Releases**: https://github.com/cilium/cilium/releases
- **Hetzner Talos Module**: https://registry.terraform.io/modules/hcloud-talos/talos/hcloud/

---

**Last Updated**: 2025-12-02  
**Cluster**: Hetzner Datacluster  
**Maintainer**: Platform Team
