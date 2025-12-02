# Talos OS Configuration

This guide covers Talos OS configuration for the datacluster. Talos is an immutable, API-managed Linux distribution designed specifically for Kubernetes.

---

## Current Configuration

**Cluster:**
- **Name**: datacluster
- **Talos Version**: v1.11.5
- **Kubernetes Version**: v1.34.1
- **Endpoint**: `https://kube.cluster.local:6443`

**Nodes:**
- **control-plane-1**: 10.0.1.101 (CX23: 2 vCPU, 4GB RAM)
- **worker-1**: 10.0.1.201 (CX33: 4 vCPU, 8GB RAM)

**System Extensions:**
- **Tailscale**: Integrated via custom Packer image

**Container Runtime:**
- **containerd**: v2.1.5 (bundled with Talos)

**Kernel:**
- **Linux**: 6.12.57-talos

---

## Configuration Management

### Terraform-Managed Approach (Current)

Talos configuration is generated and applied automatically by Terraform during cluster creation. No manual `talhelper` or `talosctl` commands needed.

**Workflow:**
1. Configure `terraform-v2/terraform.tfvars` with cluster parameters
2. Run `terraform apply`
3. Terraform providers handle:
   - `talos_machine_secrets` - Generate cluster secrets (CA certs, tokens)
   - `talos_machine_configuration_apply` - Apply configs to nodes
   - `talos_machine_bootstrap` - Bootstrap etcd on control-plane
   - `talos_cluster_kubeconfig` - Generate kubeconfig

**Configuration sources:**
- `main.tf` - Talos resources and machine configs
- `terraform.tfvars` - Cluster parameters (versions, network, node specs)

**Pros:**
- Fully automated, no manual steps
- Idempotent (can re-run terraform apply)
- GitOps-friendly (configuration as code)
- Includes secret generation and kubeconfig

**Cons:**
- Less flexible for advanced Talos features
- Harder to customize individual node configs
- Must use Terraform for all changes

---

### Manual Approach with talos/cluster.yaml (Alternative)

For advanced users needing fine-grained control, use `talos/cluster.yaml` with `talhelper` or direct `talosctl` commands.

**When to use:**
- Custom machine patches (sysctls, kubelet args, pod security)
- Node-specific configurations
- Testing Talos features before Terraform integration
- Debugging cluster bootstrap issues

**Workflow:**
1. Define cluster in `talos/cluster.yaml`
2. Generate configs with `talhelper genconfig`
3. Apply manually with `talosctl apply-config`
4. Bootstrap with `talosctl bootstrap`

See `talos/README.md` for detailed manual setup (if needed).

---

## Talos Features Used

### 1. Immutable OS

- **No SSH access** - All management via Talos API (port 50000)
- **No package manager** - System extensions only
- **Read-only root filesystem** - Changes require reboot
- **API-driven updates** - `talosctl upgrade` or recreate with Terraform

**Benefits:**
- Reduced attack surface (no shell, no login)
- Predictable state (no drift from manual changes)
- Easy rollback (boot previous image)

---

### 2. System Extensions

Extensions add functionality without modifying core OS. Currently using:
- **siderolabs/tailscale** - WireGuard VPN for secure access

**How extensions are integrated:**
1. Define in `_packer/schematic.yaml`
2. Build custom image with Packer (includes extensions in image)
3. Deploy with Terraform (nodes boot with extensions loaded)

**Extension lifecycle:**
- Loaded at boot from `/system/extensions` (immutable)
- Updates require rebuilding Packer image
- No runtime installation (unlike Linux packages)

---

### 3. Cloud Controller Manager (CCM)

Two CCMs run in parallel:
- **Hetzner CCM** (`hcloud-cloud-controller-manager`) - Manages Hetzner LoadBalancers, Routes
- **Talos CCM** (`talos-cloud-controller-manager`) - Node lifecycle, labels

Both deployed automatically by Terraform.

---

### 4. Container Runtime

**containerd** v2.1.5 (built into Talos):
- Kubernetes CRI-compatible
- Optimized for Kubernetes (no Docker daemon)
- Managed by Talos (no direct configuration)

**Container image sources:**
- Default: `registry.k8s.io` (Kubernetes images)
- Custom: Any OCI-compatible registry (Docker Hub, ghcr.io, private registries)

---

### 5. Networking

**CNI**: Cilium v1.18.3 (deployed by Terraform Helm provider)
- eBPF-based dataplane (faster than iptables)
- Pod-to-pod encryption capable (not enabled)
- Network policies supported
- Hubble observability available

**Network configuration:**
- **Cluster network**: 10.0.0.0/16 (private)
- **Node subnet**: 10.0.1.0/24
- **Pod CIDR**: 10.0.16.0/20 (4096 IPs per node)
- **Service CIDR**: 10.0.8.0/21 (2048 ClusterIPs)

---

### 6. Control Plane Configuration

**Scheduler:**
- Runs workloads on control-plane (cost optimization)
- Toleration: `node-role.kubernetes.io/control-plane:NoSchedule-`

**API Server:**
- Exposed on public IP (port 6443)
- Protected by Hetzner firewall (allow from any, but TLS-encrypted)
- Certificate SANs: `kube.cluster.local`, control-plane IP

**etcd:**
- Single-node etcd (control-plane-1)
- No external storage (embedded in Talos)
- Automatic backups (Talos etcd snapshot feature)

---

## Talos Operations

### Access Talos API

```bash
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
talosctl -n <CONTROL_PLANE_PUBLIC_IP> version
talosctl -n <CONTROL_PLANE_PUBLIC_IP> dashboard
```

### View System Logs

```bash
# All services
talosctl -n <node-ip> logs

# Specific service
talosctl -n <node-ip> logs kubelet
talosctl -n <node-ip> logs etcd

# Follow logs
talosctl -n <node-ip> logs -f containerd
```

### Check Cluster Health

```bash
# Node services
talosctl -n <control-plane-ip> services

# etcd members
talosctl -n <control-plane-ip> etcd members

# Cluster membership
talosctl -n <node-ip> get members

# Time sync (important for etcd)
talosctl -n <node-ip> time status
```

### Restart Services

```bash
# Restart kubelet
talosctl -n <node-ip> service kubelet restart

# Restart containerd
talosctl -n <node-ip> service containerd restart
```

### Execute Commands in Container

Talos doesn't have shell access, but you can run ephemeral containers:

```bash
# Debug network
talosctl -n <node-ip> run --image=nicolaka/netshoot:latest --interactive --tty -- bash

# Check DNS
talosctl -n <node-ip> run --image=busybox:latest --interactive --tty -- nslookup kubernetes.default.svc.cluster.local
```

---

## Machine Configuration Details

Generated by Terraform, but key settings include:

### Control Plane Config

```yaml
machine:
  type: controlplane
  kubelet:
    nodeIP:
      validSubnets:
        - 10.0.1.0/24  # Use private network IP
    extraArgs:
      rotate-server-certificates: "true"
  network:
    hostname: control-plane-1
    interfaces:
      - interface: eth0
        dhcp: true
        vip:
          ip: <placeholder-for-failover>  # Future multi-master
  sysctls:
    net.ipv4.ip_forward: "1"  # Required for Cilium
    net.bridge.bridge-nf-call-iptables: "1"

cluster:
  controlPlane:
    endpoint: https://kube.cluster.local:6443
  network:
    cni:
      name: none  # Cilium deployed separately via Helm
    podSubnets:
      - 10.0.16.0/20
    serviceSubnets:
      - 10.0.8.0/21
```

### Worker Config

```yaml
machine:
  type: worker
  kubelet:
    nodeIP:
      validSubnets:
        - 10.0.1.0/24
    extraArgs:
      rotate-server-certificates: "true"
  network:
    hostname: worker-1
    interfaces:
      - interface: eth0
        dhcp: true
  sysctls:
    net.ipv4.ip_forward: "1"
    net.bridge.bridge-nf-call-iptables: "1"
```

**Note:** Full configs generated by Terraform are ephemeral (not committed to Git). View with:
```bash
talosctl -n <node-ip> get machineconfig -o yaml
```

---

## Talos Updates

### Patch Updates (v1.11.5 → v1.11.6)

**Requires rebuilding Packer images** (Talos is immutable).

1. Build new Packer image with v1.11.6
2. Update `terraform.tfvars` with new snapshot ID
3. Run `terraform destroy && terraform apply`

See [VERSION-UPDATES.md](../VERSION-UPDATES.md) for detailed steps.

---

### Major Updates (v1.11.x → v1.12.0)

**WARNING:** Review breaking changes at https://www.talos.dev/v1.12/introduction/what-is-new/

1. Check Kubernetes compatibility matrix
2. Test in staging environment
3. Rebuild Packer images with v1.12.0
4. Update Terraform configuration
5. Recreate cluster with `terraform destroy && apply`

**Rollback:** Keep previous Packer snapshot, revert `terraform.tfvars` to old version.

---

## Troubleshooting

### Node not joining cluster

**Symptoms:** Node shows in `hcloud server list` but not `kubectl get nodes`

**Diagnosis:**
```bash
talosctl -n <node-ip> logs kubelet
talosctl -n <node-ip> get members
talosctl -n <node-ip> services
```

**Common causes:**
- Network misconfiguration (check private network attachment)
- etcd not bootstrapped (run `talosctl -n <control-plane-ip> bootstrap`)
- Certificate mismatch (regenerate with `terraform destroy && apply`)

---

### etcd cluster unhealthy

**Symptoms:** Control plane components not starting, `kubectl` timeouts

**Diagnosis:**
```bash
talosctl -n <control-plane-ip> etcd members
talosctl -n <control-plane-ip> logs etcd
```

**Fix:**
- Single-node etcd: Destroy and recreate cluster
- Multi-node etcd: Remove unhealthy member, add new one

---

### Kubelet not starting

**Symptoms:** Node in `NotReady` state

**Diagnosis:**
```bash
talosctl -n <node-ip> service kubelet status
talosctl -n <node-ip> logs kubelet
```

**Common causes:**
- Cilium CNI not deployed (`kubectl get pods -n kube-system`)
- Misconfigured kubelet args in machine config
- Image pull failure (check containerd logs)

---

### Time drift

**Symptoms:** etcd errors, certificate validation failures

**Diagnosis:**
```bash
talosctl -n <node-ip> time status
```

**Fix:**
- Talos syncs time via NTP automatically
- Check NTP servers: `talosctl -n <node-ip> get timeservers`
- Restart time service: `talosctl -n <node-ip> service timed restart`

---

## Advanced Topics

### Custom Talos Patches

For features not exposed in Terraform (sysctls, extra mounts, custom CAs), use machine config patches:

**In Terraform:**
```hcl
# main.tf
data "talos_machine_configuration" "control_plane" {
  # ... existing config ...
  
  config_patches = [
    yamlencode({
      machine = {
        sysctls = {
          "fs.inotify.max_user_watches" = "1048576"
        }
      }
    })
  ]
}
```

**Or via talos/cluster.yaml** (manual approach):
```yaml
patches:
  - |-
    machine:
      sysctls:
        fs.inotify.max_user_watches: "1048576"
```

---

### Multi-Master Setup

Current setup uses single control-plane. For HA, add more control planes:

**In terraform.tfvars:**
```hcl
control_planes = [
  { name = "control-plane-1", type = "cx23" },
  { name = "control-plane-2", type = "cx23" },
  { name = "control-plane-3", type = "cx23" }
]
```

**Requirements:**
- 3+ control planes (etcd quorum)
- Shared VIP or load balancer for API endpoint
- Increased cost (€3.75 × 3 = €11.25/month just for control planes)

---

### Talos Image Customization

Beyond system extensions, customize Talos image with:
- Custom kernel modules (proprietary drivers)
- Custom CAs (corporate SSL intercept)
- Custom container runtime configuration

**Build process:**
1. Create advanced schematic at https://factory.talos.dev/
2. Update `_packer/schematic.yaml`
3. Rebuild with Packer

---

## Additional Resources

- **[Talos Documentation](https://www.talos.dev/latest/)** - Official docs
- **[Talos API Reference](https://www.talos.dev/latest/reference/api/)** - API details
- **[Talos System Extensions](https://github.com/siderolabs/extensions)** - Available extensions
- **[Talos Image Factory](https://factory.talos.dev/)** - Custom image builder
- **[Terraform Talos Provider](https://registry.terraform.io/providers/siderolabs/talos/latest/docs)** - Provider docs
- **[_packer/README.md](../_packer/README.md)** - Custom image building
- **[VERSION-UPDATES.md](../VERSION-UPDATES.md)** - Update procedures
