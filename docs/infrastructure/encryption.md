# SOPS Encryption Guide

This repository uses **SOPS (Secrets OPerationS)** with **age** encryption to protect sensitive data in Git.

## ⚠️ CRITICAL: Encrypt Before Committing

**NEVER commit these files unencrypted:**
- `talos/cluster.yaml` (contains IPs, API tokens, cluster secrets)
- `terraform/terraform.tfvars` (Hetzner API tokens)
- Any Kubernetes Secret manifests with real credentials
- `.env` files with passwords or keys

## Setup (First Time)

### 1. Install Tools

```bash
# macOS
brew install sops age

# Linux
curl -LO https://github.com/mozilla/sops/releases/download/v3.8.1/sops-v3.8.1.linux.amd64
sudo mv sops-v3.8.1.linux.amd64 /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops

curl -LO https://github.com/FiloSottile/age/releases/download/v1.1.1/age-v1.1.1-linux-amd64.tar.gz
tar xzf age-v1.1.1-linux-amd64.tar.gz
sudo mv age/age age/age-keygen /usr/local/bin/
```

### 2. Generate Age Key

```bash
# From repository root
age-keygen -o age.key

# Output shows:
# Public key: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Save this public key - you'll need it for .sops.yaml
```

**CRITICAL: Backup age.key securely!**
- Store in password manager (1Password, Bitwarden)
- Keep offline backup (USB drive, paper wallet)
- **Loss = permanent data loss** (cannot decrypt secrets)

### 3. Create .sops.yaml

```bash
# Repository root
cat > .sops.yaml <<EOF
creation_rules:
  - path_regex: talos/cluster\.yaml$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Your public key
  - path_regex: terraform/.*\.tfvars$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  - path_regex: infrastructure/.*/.*secret.*\.yaml$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  - path_regex: .*\.enc$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
```

Replace `age1xxx...` with your public key from step 2.

### 4. Set Environment Variable

```bash
# Add to ~/.bashrc or ~/.zshrc
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age.key"

# Or per-session
export SOPS_AGE_KEY_FILE=/path/to/datacluster/age.key
```

## Encrypting Files

### Talos Cluster Config

```bash
# After editing talos/cluster.yaml
sops --encrypt --in-place talos/cluster.yaml

# File is now encrypted, safe to commit
git add talos/cluster.yaml
git commit -m "Update cluster config"
```

### Terraform Variables

```bash
cd terraform
# Edit terraform.tfvars with real values
nano terraform.tfvars

# Encrypt
sops --encrypt terraform.tfvars > terraform.tfvars.enc

# Delete plaintext
rm terraform.tfvars

# Commit encrypted version
git add terraform.tfvars.enc
git commit -m "Add Hetzner credentials"
```

### Kubernetes Secrets

```bash
# Create secret manifest
cat > infrastructure/storage/s3-credentials.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: s3-credentials
  namespace: spark-operator
stringData:
  access-key: "YOUR_ACCESS_KEY"
  secret-key: "YOUR_SECRET_KEY"
EOF

# Encrypt
sops --encrypt --in-place infrastructure/storage/s3-credentials.yaml

# Safe to commit
git add infrastructure/storage/s3-credentials.yaml
```

## Decrypting Files

### Edit Encrypted File

```bash
# Opens in editor, decrypts on-the-fly
sops talos/cluster.yaml

# Save and quit - file auto-encrypted
```

### Decrypt to Stdout

```bash
# View contents without writing to disk
sops -d talos/cluster.yaml

# Use in scripts
sops -d terraform/terraform.tfvars.enc > terraform/terraform.tfvars
terraform apply
rm terraform/terraform.tfvars  # Clean up
```

### Decrypt for Talhelper

```bash
# Generate Talos configs from encrypted cluster.yaml
sops -d talos/cluster.yaml | talhelper genconfig -o talos/generated /dev/stdin

# Or decrypt temporarily
sops -d talos/cluster.yaml > talos/cluster-decrypted.yaml
talhelper genconfig -o talos/generated talos/cluster-decrypted.yaml
rm talos/cluster-decrypted.yaml
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
- name: Setup SOPS
  run: |
    echo "${{ secrets.SOPS_AGE_KEY }}" > age.key
    export SOPS_AGE_KEY_FILE=$PWD/age.key

- name: Decrypt and apply
  run: |
    sops -d talos/cluster.yaml > cluster-plain.yaml
    talhelper genconfig -o generated cluster-plain.yaml
```

Store age.key contents in GitHub Secrets as `SOPS_AGE_KEY`.

## Verification

### Check if File is Encrypted

```bash
# Encrypted files contain SOPS metadata
head -n 5 talos/cluster.yaml

# Should show:
# clusterName: ENC[AES256_GCM,data:xxxx,...]
# sops:
#   age:
#     - recipient: age1xxx...
```

### Pre-commit Hook

Prevent committing plaintext secrets:

```bash
# .git/hooks/pre-commit
#!/bin/bash
FILES=$(git diff --cached --name-only)

for FILE in $FILES; do
  if [[ $FILE =~ cluster\.yaml$ ]] || [[ $FILE =~ \.tfvars$ ]]; then
    if ! grep -q "sops:" "$FILE"; then
      echo "ERROR: $FILE is not encrypted!"
      echo "Run: sops --encrypt --in-place $FILE"
      exit 1
    fi
  fi
done
```

```bash
chmod +x .git/hooks/pre-commit
```

## Key Rotation

### Generate New Key

```bash
age-keygen -o age-new.key
# Public key: age1yyyyyyyyyy...
```

### Re-encrypt All Files

```bash
# Update .sops.yaml with new public key
nano .sops.yaml

# Rotate keys
export SOPS_AGE_KEY_FILE=age.key  # Old key
sops rotate --in-place talos/cluster.yaml

# Repeat for all encrypted files
find . -type f \( -name "*.yaml" -o -name "*.tfvars.enc" \) -exec sops rotate --in-place {} \;

# Replace old key
mv age-new.key age.key
```

## Troubleshooting

### Error: no key could decrypt

- Verify `SOPS_AGE_KEY_FILE` points to correct key
- Check age.key matches public key in `.sops.yaml`
- Restore from backup if key lost

### Error: cannot get decrypt key from vault

- File already encrypted, use `sops <file>` to edit
- Or decrypt first: `sops -d file > file-plain`

### Accidentally committed plaintext

```bash
# Remove from Git history immediately
git filter-repo --path-to-delete talos/cluster.yaml
git push --force

# Rotate compromised credentials (Hetzner tokens, etc.)
# Re-encrypt with new values
```

## Best Practices

1. **Always encrypt before first commit** of sensitive files
2. **Never decrypt to tracked files** (use `.gitignore`)
3. **Backup age.key** in multiple secure locations
4. **Rotate keys annually** or after team changes
5. **Use pre-commit hooks** to prevent leaks
6. **Audit with `git log -p`** periodically for exposed secrets
