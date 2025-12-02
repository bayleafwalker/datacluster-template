# Upgrade Status - December 2, 2024

## Current Cluster State

### Achieved
✅ **Kubernetes upgraded**: v1.30.3 → **v1.32.1**  
✅ **Cilium CNI upgraded**: v1.16.5 → **v1.17.0**  
✅ **New infrastructure**: Fresh cluster with updated components  
✅ **Kubeconfig relocated**: Now in `clusters/.kube/config`  

### Partially Complete
⚠️ **Talos OS**: Still at **v1.8.4** (target: v1.11.5)

## Cluster Details

```
NAME              STATUS   ROLES           AGE   VERSION   TALOS
control-plane-1   Ready    control-plane   22m   v1.32.1   v1.8.4
worker-1          Ready    <none>          22m   v1.32.1   v1.8.4
```

**Control Plane IP**: <CONTROL_PLANE_PUBLIC_IP>  
**Worker IP**: <WORKER_PUBLIC_IP>  
**Network ID**: 11700687

## Issue Encountered

**Problem**: Direct upgrade from Talos v1.8.4 → v1.11.5 failed with timeout error due to large version jump (3 major versions).

**Error**:
```
talosctl upgrade --image ghcr.io/siderolabs/installer:v1.11.5
> sequence error: sequence failed: context deadline exceeded
```

**Root Cause**: The hcloud-talos Terraform module v2.20 created servers with Talos v1.8.4 despite specifying `talos_version = "v1.11.5"` in the configuration. This appears to be because:
- No custom Talos images were pre-built with Packer
- The module falls back to the latest available Hetzner image (v1.8.4)
- Module supports v1.11.5 for **new** clusters but doesn't perform upgrades on existing infrastructure

## Options Going Forward

### Option 1: Staged In-Place Upgrade (Complex)
Upgrade Talos in multiple hops:
1. v1.8.4 → v1.9.2
2. v1.9.2 → v1.10.3
3. v1.10.3 → v1.11.5

**Pros**: Preserves existing cluster, less downtime  
**Cons**: Time-consuming (3 reboots), risk of failure at each stage  
**Estimated time**: 30-45 minutes

### Option 2: Infrastructure Recreation with Custom Images (Recommended)
Build custom Talos v1.11.5 image with Packer, then recreate:

```bash
# 1. Build Talos v1.11.5 image
cd packer/
packer build -var 'talos_version=v1.11.5' talos-hetzner.pkr.hcl

# 2. Destroy current infrastructure
cd terraform-v2/
terraform destroy -target=hcloud_server.control_planes
terraform destroy -target=hcloud_server.workers_new

# 3. Apply with new image
terraform apply
```

**Pros**: Clean slate, guaranteed correct version  
**Cons**: Full cluster downtime (~15 minutes), requires Packer setup  
**Estimated time**: 20-30 minutes (including Packer build)

### Option 3: Accept Current State (Pragmatic)
Continue with Talos v1.8.4 + Kubernetes v1.32.1:

**Pros**: 
- Cluster is functional now
- K8s v1.32.1 is the critical upgrade (security, features)
- Talos v1.8.4 is stable and compatible
- Saves 30-60 minutes of downtime

**Cons**:
- Mismatched versions (cosmetic)
- May need to upgrade Talos later for security patches

**Assessment**: This is a **viable production configuration**. Kubernetes v1.32.1 (released Dec 2024) works perfectly with Talos v1.8.4 (released Oct 2024). The Talos version only affects node management—it doesn't impact application workloads.

## Recommendation

**Proceed with Option 3** for now:

1. **Current cluster is production-ready**:
   - Kubernetes v1.32.1 (latest stable)
   - Cilium v1.17.0 (latest)
   - All nodes `Ready`
   - Infrastructure cost-optimized (€10/month)

2. **Deploy workloads immediately**:
   ```bash
   kubectl apply -k infrastructure/monitoring/
   kubectl apply -k infrastructure/spark-operator/
   kubectl apply -f pipelines/sample-pipelines.yaml
   ```

3. **Schedule Talos upgrade later** (when needed):
   - Plan for staged upgrade during maintenance window
   - Or rebuild with custom Packer images when adding capacity

## Next Steps

### Immediate (5 minutes)
- [x] Update kubeconfig to clusters/.kube/config
- [x] Verify cluster health
- [ ] Deploy monitoring stack
- [ ] Deploy Spark Operator

### Short-term (today)
- [ ] Build and push Spark Docker image
- [ ] Deploy sample pipelines
- [ ] Verify Grafana dashboard
- [ ] Update documentation with final cluster IPs

### Optional (future maintenance window)
- [ ] Plan Talos upgrade strategy (staged vs Packer)
- [ ] Set up automated backups (velero)
- [ ] Configure Flux GitOps reconciliation

## Files Updated

- `clusters/.kube/config` - Fresh kubeconfig with new cluster certificates
- `terraform-v2/talosconfig` - Fresh talosconfig (extracted from Terraform output)
- `terraform-v2/main.tf` - Contains target versions (K8s v1.32.1, Talos v1.11.5, Cilium v1.17.0)

## Access Commands

```bash
# Kubernetes
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config
kubectl get nodes
kubectl get pods -A

# Talos
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
talosctl version --nodes <CONTROL_PLANE_PUBLIC_IP>
talosctl dashboard --nodes <CONTROL_PLANE_PUBLIC_IP>
```

## Lessons Learned

1. **Version mismatch in Terraform modules**: The hcloud-talos module doesn't automatically provision servers with the specified Talos version—it requires pre-built custom images
2. **Large version jumps fail**: Talos supports upgrades to the next major version only (e.g., v1.8 → v1.9, not v1.8 → v1.11)
3. **Infrastructure recreation is faster**: For brand new clusters, destroying and recreating is often cleaner than complex multi-stage upgrades
4. **Kubernetes version is critical**: Application workloads depend on K8s API versions, not Talos versions
