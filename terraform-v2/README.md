# Terraform Configuration

Hetzner Cloud infrastructure managed with [hcloud-talos](https://github.com/hcloud-talos/terraform-hcloud-talos) module for automated Talos Kubernetes provisioning.

## Architecture

- **Control Plane**: 1x CX23 (2 vCPU, 4GB RAM) with workloads enabled
- **Workers**: 1x CX33 (4 vCPU, 8GB RAM)
- **Network**: 10.0.0.0/16 (nodes: 10.0.1.0/24, pods: 10.0.16.0/20, services: 10.0.8.0/21)
- **CNI**: Cilium v1.16.5
- **Tailscale**: Enabled on control plane (control-plane-only design)
- **Cost**: €10.01/month (server costs + public IPv4)

## Prerequisites

1. **Custom Talos Images** with Tailscale extension (built via Packer):
   ```bash
   cd /tmp/hcloud-talos/_packer
   export HCLOUD_TOKEN=$(cat /projects/dev/datacluster/.hetzner_api)
   ./create.sh
   ```
   
   Creates snapshots:
   - `Talos Linux v1.8.4 x86 by hcloud-talos` (AMD64)
   - `Talos Linux v1.8.4 ARM by hcloud-talos` (ARM64)

2. **Tailscale Auth Key** (stored in `.tailscale_key`, SOPS-encrypted in `terraform.tfvars.enc`)
   - Generate at https://login.tailscale.com/admin/settings/keys
   - Settings: Reusable=Yes, Ephemeral=No, Preauthorized=Yes

3. **SOPS Encryption** configured (age key at `/projects/dev/datacluster/age.key`)

## Deployment

### Initial Setup

```bash
# Navigate to directory
cd /projects/dev/datacluster/terraform-v2

# Initialize Terraform (downloads hcloud-talos module)
terraform init

# Decrypt variables
export SOPS_AGE_KEY_FILE=/projects/dev/datacluster/age.key
sops -d terraform.tfvars.enc > terraform.tfvars

# Preview changes
terraform plan

# Deploy cluster
terraform apply

# Clean up decrypted file
rm terraform.tfvars
```

### Access the Cluster

```bash
# Extract kubeconfig
terraform output -raw kubeconfig > kubeconfig

# Extract talosconfig
terraform output -raw talosconfig > ~/.talos/config

# Set kubectl context
export KUBECONFIG=$PWD/kubeconfig

# Verify nodes
kubectl get nodes -o wide

# Check Tailscale status (nodes should appear in your Tailscale network)
tailscale status
```

### Verify Tailscale Integration

```bash
# Check node Tailscale IPs
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAILSCALE-IP:.status.addresses[?(@.type=='InternalIP')].address

# Access Kubernetes API via Tailscale
# (Update kubeconfig server to use Tailscale IP of control plane)
kubectl --server=https://<TAILSCALE_IP>:6443 get nodes
```

## Module Configuration

Key parameters in `main.tf`:

```hcl
module "talos" {
  source  = "hcloud-talos/talos/hcloud"
  version = "~> 2.20"
  
  hcloud_token    = var.hcloud_token
  cluster_name    = "datacluster"
  datacenter_name = "hel1-dc2"
  
  talos_version      = "v1.8.4"
  kubernetes_version = "v1.30.3"
  
  control_plane_count            = 1
  control_plane_server_type      = "cx23"  # Cost-optimized CX series
  control_plane_allow_schedule   = true  # Cost optimization
  
  worker_nodes = [{
    type   = "cx33"  # Cost-optimized CX series
    count  = 1
  }]
  
  tailscale = {
    enabled  = true
    auth_key = var.tailscale_auth_key
  }
  
  cilium_version = "v1.16.5"
}
```

## Upgrades

### Talos/Kubernetes Version

1. Build new Packer images with updated version:
   ```bash
   cd /tmp/hcloud-talos/_packer
   # Update talos_version in hcloud.auto.pkrvars.hcl
   ./create.sh
   ```

2. Update `main.tf`:
   ```hcl
   talos_version      = "v1.8.5"
   kubernetes_version = "v1.30.4"
   ```

3. Apply:
   ```bash
   terraform apply
   ```

### Module Version

```bash
# Update version in main.tf
module "talos" {
  source  = "hcloud-talos/talos/hcloud"
  version = "~> 2.21"  # Updated
  ...
}

terraform init -upgrade
terraform plan
terraform apply
```

## Troubleshooting

### Nodes Not Joining Tailscale

```bash
# Check Tailscale extension loaded
talosctl -n <NODE_IP> get extensions

# Check Tailscale service status
talosctl -n <NODE_IP> service tailscaled

# View logs
talosctl -n <NODE_IP> logs tailscaled
```

### Cluster Bootstrap Stuck

```bash
# Check bootstrap status
terraform show | grep talos_machine_bootstrap

# Manual bootstrap (if needed)
talosctl bootstrap -n <CONTROL_PLANE_IP>
```

### Module Not Finding Custom Images

```bash
# Verify images have correct labels
hcloud image describe <IMAGE_ID>
# Should have: os=talos

# Module automatically selects most recent image with os=talos label
```

## Files

- `main.tf` - Module configuration, providers, network setup
- `variables.tf` - Input variable declarations
- `outputs.tf` - Kubeconfig, talosconfig, node IPs
- `terraform.tfvars.enc` - SOPS-encrypted credentials (Hetzner token, Tailscale key)
- `terraform.tfvars.example` - Template for credentials

## Cost Breakdown

| Resource | Type | Monthly Cost |
|----------|------|--------------|
| Control Plane | CX23 | €3.75 |
| Worker | CX33 | €6.26 |
| Public IPv4 × 2 | Primary IPs | €1.26 |
| Network | Hetzner Cloud Network | €0 (included) |
| Firewall | Hetzner Cloud Firewall | €0 (included) |
| **Total** | | **€10.01/month** |

*Note: Public IPv4 cost is unavoidable - Hetzner Cloud Networks don't provide NAT gateway.*

## Security Notes

- **ALWAYS** SOPS-encrypt `terraform.tfvars` before committing
- Tailscale auth key has 5-day expiration (regenerate if needed)
- Firewall allows 0.0.0.0/0 by design (access secured via Tailscale mesh)
- Nodes join your Tailscale network automatically via preauthorized key

## References

- [hcloud-talos Module](https://github.com/hcloud-talos/terraform-hcloud-talos)
- [Talos Production Notes](https://www.talos.dev/v1.8/introduction/prodnotes/)
- [Cilium Documentation](https://docs.cilium.io/)
- [Tailscale Kubernetes Guide](https://tailscale.com/kb/1185/kubernetes/)
