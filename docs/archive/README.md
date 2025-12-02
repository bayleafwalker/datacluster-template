# Documentation Archive

This directory contains outdated or superseded documentation files preserved for historical reference.

## Archived Files

### Upgrade Documentation (Dec 2024)
- **UPGRADE-STATUS.md** - Status tracking for v1.8.4 → v1.11.5 upgrade attempt
- **POST-UPGRADE-GUIDE.md** - Post-upgrade verification steps
  - **Reason**: Upgrade completed, now covered in [VERSION-UPDATES.md](../../VERSION-UPDATES.md)

### Deployment Guides (Dec 2024)
- **DEPLOYMENT-GUIDE.md** - Old deployment procedures
- **QUICK-REFERENCE.md** - Quick reference commands
  - **Reason**: Superseded by comprehensive [README.md](../../README.md) and [docs/hetzner.md](../hetzner.md)

### Pipeline Documentation (Dec 2024)
- **PIPELINE-SUMMARY.md** - Pipeline overview and examples
  - **Reason**: Will be reorganized into [docs/pipelines.md](../pipelines.md) when Spark Operator deployed

### Old Versions (Dec 2024)
- **README.md.old** - Original minimal README
- **hetzner.md.old** - Old Hetzner provisioning guide without Packer workflow
- **talos.md.talhelper-old** - Old talhelper-based Talos setup guide
  - **Reason**: Replaced with Terraform-managed approach

## Current Active Documentation

See [../README.md](../README.md) for documentation index.

**Primary docs:**
- [README.md](../../README.md) - Getting started from scratch
- [VERSION-UPDATES.md](../../VERSION-UPDATES.md) - Update procedures
- [docs/architecture.md](../architecture.md) - System design
- [docs/hetzner.md](../hetzner.md) - Hetzner + Packer workflow
- [docs/talos.md](../talos.md) - Talos configuration
- [docs/encryption.md](../encryption.md) - SOPS workflow
- [_packer/README.md](../../_packer/README.md) - Custom image building

## Restoration

To restore archived docs (if needed):
```bash
cp docs/archive/<FILE> ./<FILE>
```

## Cleanup

Files in this archive can be safely deleted after 6 months (June 2025) if no longer referenced.
