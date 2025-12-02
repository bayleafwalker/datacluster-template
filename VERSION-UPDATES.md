# Version Update Guide

This guide covers updating Talos, Kubernetes, Cilium, and other platform components. All updates use the Packer + Terraform workflow for immutable infrastructure.

---

## Update Philosophy

**Immutable Infrastructure:** We rebuild custom Talos images with Packer and recreate clusters with Terraform rather than in-place upgrades. This ensures:
- Clean slate with no upgrade artifacts
- Tested configuration every time
- Easy rollback (revert to previous Terraform state)
- Consistent with GitOps principles

**Update Strategy:**
- **Patch versions** (v1.11.4 → v1.11.5): Safe, apply anytime
- **Minor versions** (v1.34.1 → v1.34.2): Usually safe, review changelog
- **Major versions** (v1.11.x → v1.12.0): Test thoroughly, breaking changes possible

---

## Kubernetes Version Updates

### Patch Updates (v1.34.1 → v1.34.2)

```bash
# 1. Update Terraform configuration
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops terraform.tfvars.enc

# Change kubernetes_version:
# kubernetes_version = "v1.34.2"
# Save (encrypted automatically)

# 2. Apply update (no Packer rebuild needed if Talos version unchanged)
sops -d terraform.tfvars.enc > terraform.tfvars
terraform plan
terraform apply
rm terraform.tfvars

# 3. Verify
export KUBECONFIG=$PWD/kubeconfig
kubectl version --short
kubectl get nodes
```

**Downtime:** ~2-3 minutes (rolling update, workloads migrate automatically)

---

### Minor/Major Updates (v1.34.x → v1.35.0)

**CRITICAL:** Check compatibility matrix at https://www.talos.dev/latest/introduction/support-matrix/

```bash
# 1. Verify Talos v1.11.5 supports Kubernetes v1.35.0
# See: https://www.talos.dev/v1.11/introduction/support-matrix/

# 2. Update Terraform configuration
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops terraform.tfvars.enc
# Set kubernetes_version = "v1.35.0"

# 3. Plan and review changes
sops -d terraform.tfvars.enc > terraform.tfvars
terraform plan
# Review: control plane upgrade, worker upgrade, CNI changes

# 4. Apply with automatic approval override (review carefully!)
terraform apply
rm terraform.tfvars

# 5. Verify cluster
export KUBECONFIG=$PWD/kubeconfig
kubectl version
kubectl get nodes -o wide
kubectl get pods --all-namespaces
```

**Rollback if issues:**
```bash
# Revert Terraform configuration
sops terraform.tfvars.enc
# Change kubernetes_version back to "v1.34.1"
terraform apply
```

---

## Talos OS Version Updates

Talos updates **require rebuilding Packer images** with new schematic.

### Patch Updates (v1.11.5 → v1.11.6)

```bash
# 1. Generate new schematic for Talos v1.11.6
cd _packer
curl -X POST --data-binary @schematic.yaml \
  https://factory.talos.dev/schematics
# Returns: {"id":"<NEW_SCHEMATIC_ID>"}

# 2. Verify image exists
curl -I "https://factory.talos.dev/image/<NEW_SCHEMATIC_ID>/v1.11.6/hcloud-amd64.raw.xz"
# Should return: HTTP/2 200

# 3. Update Packer configuration
nano hcloud.auto.pkrvars.hcl
# Change:
# talos_version = "v1.11.6"
# image_url_x86 = "https://factory.talos.dev/image/<NEW_SCHEMATIC_ID>/v1.11.6/hcloud-amd64.raw.xz"

# 4. Build new image
export HCLOUD_TOKEN=<your-token>
./create.sh
# Note snapshot ID (e.g., 337659999)

# 5. Update Terraform configuration
cd ../terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops terraform.tfvars.enc
# Change:
# talos_version = "v1.11.6"
# talos_image_id = 337659999  # From Packer build

# 6. Destroy and recreate cluster
sops -d terraform.tfvars.enc > terraform.tfvars
terraform destroy
terraform apply
rm terraform.tfvars

# 7. Verify
export KUBECONFIG=$PWD/kubeconfig
kubectl get nodes -o wide
# Should show: Talos (v1.11.6)

# 8. Cleanup old image
hcloud image delete <OLD_SNAPSHOT_ID>
```

**Downtime:** ~10 minutes (full cluster recreation)

---

### Major Updates (v1.11.x → v1.12.0)

**WARNING:** Major Talos updates may have breaking changes. Review https://www.talos.dev/v1.12/introduction/what-is-new/

```bash
# 1. Check compatibility
# - Does v1.12.0 support current Kubernetes version?
# - Are there breaking changes in machine config schema?
# - Does Tailscale extension work with v1.12.0?

# 2. Update schematic and build Packer image (same as patch update)
cd _packer
curl -X POST --data-binary @schematic.yaml https://factory.talos.dev/schematics
nano hcloud.auto.pkrvars.hcl
# Update talos_version and image_url_x86
export HCLOUD_TOKEN=<your-token>
./create.sh

# 3. Test in staging environment first (recommended)
# Create separate terraform-staging/ directory with same config
# Test Talos v1.12.0 before production update

# 4. Update production (same as patch update)
cd ../terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops terraform.tfvars.enc
# Update talos_version and talos_image_id
sops -d terraform.tfvars.enc > terraform.tfvars
terraform destroy
terraform apply
rm terraform.tfvars

# 5. Verify all components
kubectl get nodes
kubectl get pods --all-namespaces
talosctl -n <control-plane-ip> version
```

**Rollback:** Rebuild cluster with previous Talos version (keep old Packer image as backup).

---

## Cilium CNI Updates

### Patch/Minor Updates (v1.18.3 → v1.18.4 or v1.19.0)

```bash
# 1. Check compatibility at https://docs.cilium.io/en/stable/installation/k8s-install-helm/
# Ensure Kubernetes v1.34.1 supports Cilium v1.19.0

# 2. Update Terraform configuration
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops terraform.tfvars.enc
# Change: cilium_version = "v1.19.0"

# 3. Apply update
sops -d terraform.tfvars.enc > terraform.tfvars
terraform plan
terraform apply
rm terraform.tfvars

# 4. Verify Cilium pods
kubectl get pods -n kube-system -l k8s-app=cilium
kubectl exec -n kube-system ds/cilium -- cilium-dbg version
kubectl exec -n kube-system ds/cilium -- cilium-dbg status

# 5. Test networking
kubectl run test-nginx --image=nginx --restart=Never
kubectl expose pod test-nginx --port=80
kubectl run test-curl --image=curlimages/curl --rm -it --restart=Never -- curl http://test-nginx
kubectl delete pod test-nginx
kubectl delete service test-nginx
```

**Downtime:** Minimal (~30 seconds per node during pod rolling restart)

---

## Helm Chart Updates (Monitoring, Spark Operator)

### Prometheus + Grafana (kube-prometheus-stack)

```bash
# 1. Check latest chart version
helm search repo prometheus-community/kube-prometheus-stack

# 2. Update infrastructure/monitoring/release.yaml
cd infrastructure/monitoring
nano release.yaml
# Change spec.chart.spec.version: "XX.X.X"

# 3. Commit and let Flux reconcile (GitOps)
git add release.yaml
git commit -m "Update kube-prometheus-stack to vXX.X.X"
git push
flux reconcile kustomization monitoring

# Or apply manually:
kubectl apply -k .

# 4. Verify
kubectl get pods -n monitoring
kubectl port-forward -n monitoring svc/grafana 3000:80
```

---

### Spark Operator

```bash
# 1. Check latest operator version
helm search repo spark-operator/spark-operator

# 2. Update infrastructure/spark-operator/release.yaml
cd infrastructure/spark-operator
nano release.yaml
# Change spec.chart.spec.version: "X.X.X"

# 3. Apply (Flux or manual)
kubectl apply -k .

# 4. Verify
kubectl get pods -n spark-operator
kubectl get crd sparkapplications.sparkoperator.k8s.io
```

---

## System Extension Updates (Tailscale)

When Tailscale extension updates, rebuild Packer images:

```bash
# 1. Check for new extension version at:
# https://github.com/siderolabs/extensions/tree/main/network/tailscale

# 2. Update _packer/schematic.yaml (if extension version changes)
nano _packer/schematic.yaml
# Usually just image: ghcr.io/siderolabs/tailscale:<VERSION>

# 3. Regenerate schematic ID
curl -X POST --data-binary @schematic.yaml \
  https://factory.talos.dev/schematics
# Get new schematic ID

# 4. Rebuild Packer images (same as Talos update)
nano hcloud.auto.pkrvars.hcl
# Update image_url_x86 with new schematic ID
./create.sh

# 5. Update Terraform and recreate cluster
cd ../terraform-v2
sops terraform.tfvars.enc
# Update talos_image_id
terraform destroy && terraform apply
```

---

## Update Checklist

Before any update:

- [ ] Review changelogs for breaking changes
- [ ] Check compatibility matrix (Talos ↔ Kubernetes ↔ Cilium)
- [ ] Backup kubeconfig and talosconfig
- [ ] Backup SOPS age.key (encrypted separately)
- [ ] Test in staging environment (if available)
- [ ] Schedule maintenance window for major updates
- [ ] Document current versions (run `kubectl version`, `talosctl version`)

After update:

- [ ] Verify all nodes Ready: `kubectl get nodes`
- [ ] Verify all system pods running: `kubectl get pods -n kube-system`
- [ ] Test networking: `kubectl exec -n kube-system ds/cilium -- cilium-dbg status`
- [ ] Test workload scheduling: `kubectl run test-pod --image=nginx`
- [ ] Update documentation with new versions
- [ ] Delete old Packer images if successful

---

## Rollback Procedures

### Kubernetes Version Rollback

```bash
cd terraform-v2
export SOPS_AGE_KEY_FILE=../age.key
sops terraform.tfvars.enc
# Change kubernetes_version back to previous version
terraform apply
```

**Limitation:** Can only roll back within Talos-supported range. Check support matrix.

---

### Talos OS Rollback

```bash
# 1. Ensure old Packer image still exists
hcloud image list --selector os=talos
# Find previous snapshot ID

# 2. Update Terraform to use old image
cd terraform-v2
sops terraform.tfvars.enc
# Change:
# talos_version = "<OLD_VERSION>"
# talos_image_id = <OLD_SNAPSHOT_ID>

# 3. Recreate cluster with old version
sops -d terraform.tfvars.enc > terraform.tfvars
terraform destroy
terraform apply
rm terraform.tfvars
```

**Prevention:** Keep last 2 Packer snapshots as rollback insurance.

---

### Cilium CNI Rollback

```bash
cd terraform-v2
sops terraform.tfvars.enc
# Change cilium_version back to previous version
terraform apply
kubectl delete pods -n kube-system -l k8s-app=cilium
# Pods recreate with old version
```

---

## Automated Update Strategy (Future)

Consider implementing:

1. **Renovate Bot** - Auto-create PRs for Helm chart updates in `infrastructure/`
2. **Dependabot** - Track Terraform provider versions
3. **GitHub Actions** - Weekly check for Talos/Kubernetes releases
4. **Staging cluster** - Separate `terraform-staging/` to test updates first

---

## Version Compatibility Matrix

| Talos OS | Kubernetes | Cilium | Notes |
|----------|------------|--------|-------|
| v1.11.5  | v1.34.1    | v1.18.3 | Current production |
| v1.11.x  | v1.32-v1.34 | v1.16+ | Supported |
| v1.12.x  | v1.33-v1.35 | v1.17+ | Future (verify at release) |

**Official references:**
- Talos support: https://www.talos.dev/latest/introduction/support-matrix/
- Cilium support: https://docs.cilium.io/en/stable/installation/k8s-install-helm/
- Kubernetes versioning: https://kubernetes.io/releases/

---

## Maintenance Schedule

**Recommended update cadence:**

- **Kubernetes patches** (v1.34.1 → v1.34.2): Monthly or as CVEs released
- **Kubernetes minor** (v1.34 → v1.35): Every 2-3 releases (skip some minors)
- **Talos patches** (v1.11.5 → v1.11.6): Quarterly or as needed
- **Talos major** (v1.11 → v1.12): Annually after 2-3 months of community testing
- **Cilium updates**: When Kubernetes version requires it
- **Helm charts**: Monthly check for updates

**Emergency updates:** Apply immediately for critical CVEs (e.g., privilege escalation, remote code execution).

---

## Troubleshooting Updates

### Packer build fails after schematic update
```bash
# Verify schematic URL exists
curl -I "https://factory.talos.dev/image/<SCHEMATIC_ID>/<VERSION>/hcloud-amd64.raw.xz"
# If 404, regenerate schematic
curl -X POST --data-binary @_packer/schematic.yaml https://factory.talos.dev/schematics
```

### Terraform apply fails during cluster recreation
```bash
# Check Terraform state
terraform state list
# Manually remove stuck resources
terraform state rm <RESOURCE>
# Or force destroy
terraform destroy -target=<RESOURCE>
```

### Nodes not joining after update
```bash
# Check Talos logs
talosctl -n <node-ip> logs
# Check Talos services
talosctl -n <node-ip> services
# Verify network connectivity
talosctl -n <node-ip> get members
```

### Cilium pods crash loop after update
```bash
# Check Cilium logs
kubectl logs -n kube-system ds/cilium
# Verify Cilium config
kubectl get cm -n kube-system cilium-config -o yaml
# Rollback Cilium version
sops terraform.tfvars.enc
# Change cilium_version back, terraform apply
```

---

## Additional Resources

- **[Talos Upgrade Guide](https://www.talos.dev/latest/talos-guides/upgrading-talos/)** - Official upgrade procedures
- **[Kubernetes Version Skew](https://kubernetes.io/releases/version-skew-policy/)** - Component compatibility
- **[Cilium Upgrade Guide](https://docs.cilium.io/en/stable/operations/upgrade/)** - CNI upgrade best practices
- **[_packer/README.md](_packer/README.md)** - Custom image building details
- **[terraform-v2/README.md](terraform-v2/README.md)** - Infrastructure deployment guide
