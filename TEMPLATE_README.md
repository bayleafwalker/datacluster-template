# Datacluster Template Repository

This is a **CLEAN TEMPLATE** version of the datacluster repository suitable for public sharing.

## What Has Been Removed

All sensitive data and operational files have been removed:

### Secrets & Keys
- ✅ `age.key` - SOPS encryption key (replaced with age.key.example)
- ✅ All encrypted `.enc` files with real secrets
- ✅ `talos/cluster.yaml` - Real cluster config (replaced with cluster.yaml.example)
- ✅ `terraform-v2/terraform.tfvars` - Real Hetzner API tokens

### Generated Files
- ✅ `terraform-v2/kubeconfig` - Generated Kubernetes config
- ✅ `terraform-v2/talosconfig` - Generated Talos config
- ✅ `clusters/.kube/config` - Standard kubeconfig location
- ✅ Terraform state files (`.tfstate`, `.tfstate.backup`)
- ✅ Terraform lock files and cache (`.terraform/`)

### Git History
- ✅ Original `.git` directory removed (no commit history with secrets)
- ✅ Fresh Git repository initialized

### Placeholders Inserted
- 🔄 All IP addresses replaced with `<CONTROL_PLANE_PUBLIC_IP>`, `<WORKER_PUBLIC_IP>`, `<TAILSCALE_IP>`
- 🔄 GitHub username replaced with `<YOUR-GITHUB-USERNAME>`
- �� SOPS age keys replaced with `age1xxxxxxx...` placeholder
- 🔄 S3 credentials already contain `REPLACE_*` placeholders

## What Remains (Safe for Public)

✅ Complete infrastructure as code templates
✅ Documentation with placeholder values
✅ Kubernetes manifests with template configurations
✅ Packer build scripts (schematic IDs are public)
✅ Flux GitOps structure
✅ Example files (.example suffix)
✅ All scripts and automation

## How to Use This Template

1. **Fork this repository** to your GitHub account
2. **Follow the Getting Started guide** in README.md
3. **Generate your own secrets**:
   - Create `age.key` with `age-keygen`
   - Update `.sops.yaml` with YOUR public key
   - Create `terraform.tfvars` from example
   - Encrypt all secrets before committing

## Security Verification

The following checks have been performed:

```bash
# No real tokens or API keys
grep -r "hcloud_token.*=.*[A-Za-z0-9]" --exclude="*.example"
# No SSH keys or certificates
find . -name "*.pem" -o -name "*.key" ! -name "*.example"
# No base64-encoded secrets
grep -r "data:" infrastructure/ | grep -v "stringData"
# No GitHub tokens
grep -r "ghp_\|gho_\|github_pat_"
```

All checks passed ✅

## Original Repository

This template is based on a working production deployment.  
For questions or issues, see the documentation in `docs/`.

## License

MIT License - See LICENSE file
