# Cluster Status

## ✅ Operational

| Component | Value |
|-----------|-------|
| **Talos** | v1.8.4 |
| **Kubernetes** | v1.30.3 |
| **Nodes** | 2 (control-plane + worker) |
| **Servers** | CX23 + CX33 |
| **Cost** | €10.01/month |

---

## Infrastructure

### Servers
- **Control Plane**: CX23 (2 vCPU, 4GB RAM) - €3.75/mo
- **Worker**: CX33 (4 vCPU, 8GB RAM) - €6.26/mo
- **Public IPv4 × 2**: €1.26/mo (required for internet connectivity)

### Network
- **CIDR**: 10.0.0.0/16
- **Nodes**: 10.0.1.0/24 (control: 10.0.1.101, worker: 10.0.1.201)
- **Pods**: 10.0.16.0/20 (Cilium)
- **Services**: 10.0.8.0/21

### Security
- **Firewall**: Ports 6443 (Kube API), 50000 (Talos API) open to 0.0.0.0/0
- **VPN**: Tailscale enabled on control plane
- **Access**: Primary via Tailscale, public IPs for internet connectivity

---

## Access

### Standard Location
```bash
# Use standard kubeconfig location
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig

# Verify connection
kubectl get nodes

# Talos control plane (public IP: <CONTROL_PLANE_PUBLIC_IP>)
talosctl -n <CONTROL_PLANE_PUBLIC_IP> version

# Worker (via control plane private network)
talosctl -n 10.0.1.201 --endpoints <CONTROL_PLANE_PUBLIC_IP> version
```

### Regenerate Configs (if needed)
```bash
cd /projects/dev/datacluster/terraform-v2
terraform output -raw kubeconfig > /projects/dev/datacluster/clusters/.kube/config
```

---

## System Components

| Component | Version | Status | Pods |
|-----------|---------|--------|------|
| Cilium CNI | v1.16.5 | ✅ Running | 5 |
| CoreDNS | - | ✅ Running | 2 |
| Hetzner CCM | - | ✅ Running | 1 |
| Talos CCM | - | ✅ Running | 1 |
| Kube Control Plane | v1.30.3 | ✅ Running | 3 |

**Total System Pods**: 12 (all Running)

---

## Cost Breakdown

- CX23 control-plane: €3.75/mo
- CX33 worker: €6.26/mo  
- Public IPv4 × 2: €1.26/mo
- **Total**: €10.01/mo

Public IPv4 required (no NAT gateway available on Hetzner).

---

## Verification Commands

```bash
# Check cluster health
kubectl get nodes -o wide
kubectl get pods -A

# Check Tailscale status
tailscale status

# Check Hetzner infrastructure
hcloud server list
hcloud network list
hcloud firewall list
hcloud primary-ip list

# Verify costs
hcloud server list --output columns=name,type
# CX23: €3.75/mo, CX33: €6.26/mo, Public IPv4: €0.63/mo each
```

---

## Maintenance

```bash
# Check cluster health
kubectl get nodes
kubectl get pods -A

# Verify costs
hcloud server list

# Upgrade (rolling)
# 1. Update talos_version/kubernetes_version in main.tf
# 2. terraform apply
```

