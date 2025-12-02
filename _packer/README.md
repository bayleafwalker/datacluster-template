# Talos Image Building with Packer

This directory contains Packer configuration to build custom Talos OS images with the Tailscale extension for Hetzner Cloud.

## Prerequisites

- **Packer**: Install from https://www.packer.io/downloads or `brew install packer`
- **Hetzner Cloud API Token**: Required for creating snapshots
- **SOPS + age**: For decrypting terraform.tfvars to get HCLOUD_TOKEN

## Quick Start

### 1. Build Images with Tailscale Extension

The pre-configured setup includes the Tailscale system extension, which is required when `tailscale.enabled = true` in Terraform.

```bash
# Export Hetzner Cloud API token
export HCLOUD_TOKEN="your-hcloud-token-here"

# Or extract from SOPS-encrypted tfvars
export SOPS_AGE_KEY_FILE=../age.key
export HCLOUD_TOKEN=$(sops -d ../terraform-v2/terraform.tfvars.enc | grep hcloud_token | cut -d'"' -f2)

# Build images (both ARM64 and x86_64)
./_packer/create.sh
```

This will:
1. Initialize Packer and download required plugins
2. Create temporary Hetzner servers (cax11 for ARM, cx22 for x86)
3. Download Talos images with Tailscale extension from Image Factory
4. Write images to server disks
5. Create snapshots with labels: `os=talos`, `version=v1.9.3`, `extensions=tailscale`
6. Destroy temporary servers
7. Snapshots remain in your Hetzner project (~10-15 minutes total)

**Cost**: ~€0.01 per build (temporary servers are destroyed after snapshot creation)

### 2. Verify Images Created

```bash
# List Talos images in Hetzner Cloud
hcloud image list --selector os=talos

# Expected output:
# ID        TYPE      NAME                                          AGE
# 12345678  snapshot  Talos Linux v1.9.3 ARM with Tailscale        5m
# 12345679  snapshot  Talos Linux v1.9.3 x86 with Tailscale        5m
```

## Configuration Files

### `schematic.yaml`
Defines Talos system extensions to include in the image:

```yaml
customization:
  systemExtensions:
    officialExtensions:
      - siderolabs/tailscale
```

**Adding more extensions**:
```yaml
customization:
  systemExtensions:
    officialExtensions:
      - siderolabs/tailscale
      - siderolabs/iscsi-tools      # For iSCSI storage
      - siderolabs/util-linux-tools # Additional utilities
```

### `hcloud.auto.pkrvars.hcl`
Packer variables configuration:

```hcl
# Talos version - MUST match terraform-v2/main.tf
talos_version = "v1.9.3"

# Custom image URLs (generated from schematic.yaml)
image_url_arm = "https://factory.talos.dev/image/<SCHEMATIC_ID>/v1.9.3/hcloud-arm64.raw.xz"
image_url_x86 = "https://factory.talos.dev/image/<SCHEMATIC_ID>/v1.9.3/hcloud-amd64.raw.xz"

# Hetzner datacenter (Helsinki)
server_location = "hel1"
```

### `talos-hcloud.pkr.hcl`
Packer build definition (no modifications needed unless changing server types or labels).

## Customizing Extensions

### Step 1: Update schematic.yaml

Add or remove extensions from the official Talos extensions list:
https://github.com/siderolabs/extensions

```yaml
customization:
  systemExtensions:
    officialExtensions:
      - siderolabs/tailscale
      - siderolabs/nvidia-container-toolkit  # For GPU workloads
      - siderolabs/qemu-guest-agent          # For virtualization
```

### Step 2: Generate New Schematic ID

```bash
cd _packer/
curl -X POST --data-binary @schematic.yaml https://factory.talos.dev/schematics
```

**Example output**:
```json
{"id":"ce7e638f00b0da165e065ec4bc80df0e8e08e190e8d2006a7ebff08b2cb32961"}
```

### Step 3: Update Image URLs

Edit `hcloud.auto.pkrvars.hcl` with the new schematic ID:

```hcl
image_url_arm = "https://factory.talos.dev/image/NEW_SCHEMATIC_ID/v1.9.3/hcloud-arm64.raw.xz"
image_url_x86 = "https://factory.talos.dev/image/NEW_SCHEMATIC_ID/v1.9.3/hcloud-amd64.raw.xz"
```

### Step 4: Rebuild Images

```bash
./_packer/create.sh
```

## Upgrading Talos Versions

When a new Talos version is released:

### 1. Check Compatibility

- **Kubernetes compatibility**: https://www.talos.dev/latest/introduction/support-matrix/
- **Cilium compatibility**: https://docs.cilium.io/en/stable/network/kubernetes/compatibility/

### 2. Update Version Files

Edit `_packer/hcloud.auto.pkrvars.hcl`:
```hcl
talos_version = "v1.10.0"  # New version
image_url_arm = "https://factory.talos.dev/image/<SCHEMATIC_ID>/v1.10.0/hcloud-arm64.raw.xz"
image_url_x86 = "https://factory.talos.dev/image/<SCHEMATIC_ID>/v1.10.0/hcloud-amd64.raw.xz"
```

Edit `terraform-v2/main.tf`:
```hcl
talos_version      = "v1.10.0"  # Must match Packer version
kubernetes_version = "v1.33.0"  # Check compatibility matrix
```

### 3. Delete Old Images (Optional)

```bash
# List existing images
hcloud image list --selector os=talos

# Delete old versions
hcloud image delete "Talos Linux v1.9.3 ARM with Tailscale"
hcloud image delete "Talos Linux v1.9.3 x86 with Tailscale"
```

### 4. Build New Images

```bash
./_packer/create.sh
```

### 5. Recreate Cluster

```bash
cd terraform-v2/
export SOPS_AGE_KEY_FILE=../age.key
sops -d terraform.tfvars.enc > terraform.tfvars
terraform destroy -auto-approve  # Destroys cluster
terraform apply -auto-approve    # Creates with new images
rm terraform.tfvars
```

## Troubleshooting

### Issue: "Error: no matching image found"

**Cause**: Terraform can't find images with label `os=talos`

**Solution**:
```bash
# Verify images exist
hcloud image list --selector os=talos

# If missing, rebuild
export HCLOUD_TOKEN=$(sops -d ../terraform-v2/terraform.tfvars.enc | grep hcloud_token | cut -d'"' -f2)
./_packer/create.sh
```

### Issue: "Packer timeout downloading image"

**Cause**: Talos Image Factory may be slow or schematic ID invalid

**Solution**:
1. Verify schematic ID is correct (check `curl` output)
2. Test image URL manually:
   ```bash
   wget --spider "https://factory.talos.dev/image/<SCHEMATIC_ID>/v1.9.3/hcloud-arm64.raw.xz"
   ```
3. Increase timeout in `talos-hcloud.pkr.hcl` (default: 5 retries)

### Issue: "HCLOUD_TOKEN not set"

**Solution**:
```bash
# Option 1: Extract from SOPS
export SOPS_AGE_KEY_FILE=../age.key
export HCLOUD_TOKEN=$(sops -d ../terraform-v2/terraform.tfvars.enc | grep hcloud_token | cut -d'"' -f2)

# Option 2: Export directly (less secure, not committed)
export HCLOUD_TOKEN="your-token-here"

# Option 3: Let script prompt (interactive)
./_packer/create.sh  # Will ask for token
```

### Issue: "Image too old for Kubernetes version"

**Cause**: Talos version doesn't support specified Kubernetes version

**Solution**: Check compatibility matrix and update both versions together:
```bash
# Example for K8s 1.33.x
talos_version      = "v1.10.0"
kubernetes_version = "v1.33.2"
```

Compatibility: https://www.talos.dev/latest/introduction/support-matrix/

## Version History

| Talos Version | Kubernetes | Cilium | Date       | Notes                     |
|---------------|------------|--------|------------|---------------------------|
| v1.9.3        | v1.32.3    | v1.17.0| 2024-12-02 | Initial production setup  |
| v1.8.4        | v1.30.3    | v1.16.5| 2024-12-01 | Testing (not deployed)    |

## Cost Analysis

**Image Building**:
- Temporary server costs: ~€0.01 per build (CX22 + CAX11 for ~10 minutes)
- Snapshot storage: FREE (images stored as snapshots in Hetzner project)
- No recurring costs for storing images

**Best Practices**:
1. Build images once per Talos version
2. Reuse images across multiple clusters
3. Delete old images when upgrading to reduce clutter
4. Test new images in non-production first

## Integration with Terraform

The hcloud-talos Terraform module automatically discovers images with `os=talos` label:

```hcl
# terraform-v2/main.tf
module "talos" {
  source  = "hcloud-talos/talos/hcloud"
  version = "~> 2.20"
  
  talos_version      = "v1.9.3"  # Must match Packer
  kubernetes_version = "v1.32.3"
  cilium_version     = "v1.17.0"
  
  # Tailscale configuration (requires extension in image)
  tailscale = {
    enabled  = true
    auth_key = var.tailscale_auth_key
  }
}
```

The module selects images based on architecture:
- **CX/CPX server types** → x86 image
- **CAX server types** → ARM64 image

## References

- **Talos Image Factory**: https://factory.talos.dev/
- **Talos Extensions**: https://github.com/siderolabs/extensions
- **hcloud-talos Module**: https://github.com/hcloud-talos/terraform-hcloud-talos
- **Packer Hetzner Plugin**: https://github.com/hetznercloud/packer-plugin-hcloud
- **Tailscale Extension**: https://github.com/siderolabs/extensions/tree/main/network/tailscale
