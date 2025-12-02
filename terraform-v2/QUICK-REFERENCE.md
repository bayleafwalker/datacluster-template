# Quick Reference

## Cluster Access

```bash
# Kubectl (via Tailscale)
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig
kubectl get nodes

# Talosctl (control-plane)
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
talosctl -n <TAILSCALE_IP> version

# Talosctl (worker via control-plane)
talosctl -n 10.0.1.201 --endpoints <CONTROL_PLANE_IP> version
```

## Infrastructure

| Component | Type | Private IP |
|-----------|------|------------|
| control-plane | CX23 | 10.0.1.101 |
| worker | CX33 | 10.0.1.201 |

Network: 10.0.0.0/16 • Cost: €10.01/mo

---

## 🔧 Common Operations

### Apply Terraform Changes
```bash
cd /projects/dev/datacluster/terraform-v2
export SOPS_AGE_KEY_FILE=/projects/dev/datacluster/age.key
sops -d terraform.tfvars.enc > terraform.tfvars
terraform plan
terraform apply
rm terraform.tfvars  # Important!
```

### Regenerate Configs
```bash
cd /projects/dev/datacluster/terraform-v2
terraform output -raw kubeconfig > kubeconfig
terraform output -raw talosconfig > talosconfig
chmod 600 kubeconfig talosconfig
```

### Check Cluster Health
```bash
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig
kubectl get nodes
kubectl get pods -A
kubectl top nodes  # requires metrics-server
```

### Worker Reboot (if needed)
```bash
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
talosctl -n 10.0.1.201 --endpoints <WORKER_PUBLIC_IP> reboot
```

---

## 📦 Versions

- **Talos OS**: v1.8.4 (custom image with Tailscale v1.72.1)
- **Kubernetes**: v1.30.3
- **Cilium**: v1.16.5
- **hcloud-talos module**: v2.20.7

## Troubleshooting

**Worker not Ready:**
```bash
kubectl describe node worker-1
terraform taint 'module.talos.hcloud_server.workers_new["worker-1"]'
terraform apply
```

**Certificate errors:**
```bash
terraform output -raw talosconfig > talosconfig
chmod 600 talosconfig
```
