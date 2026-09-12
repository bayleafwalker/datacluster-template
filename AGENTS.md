# Datacluster Template Agent Guidance

> Shared environment guidance lives in `/projects/dev/AGENTS.md`.

This repository is the template the Hetzner-oriented Talos, Terraform, Packer,
Flux and data-platform clusters are cut from. Nothing here addresses a live
cluster, and no real address, token or key belongs in it — keep every example
value a placeholder. Changes still land in downstream clusters, so treat them as
potentially cost-bearing and externally visible there.

A cluster repository cut from this template sets `REPO_ROOT` to its own checkout;
the commands below use it rather than a hardcoded path.

- Locate the specific Terraform or Packer module before changing it; do not
  rely on historical README paths as current module layout.
- Keep SOPS-encrypted configuration encrypted in Git. Never add `age.key`,
  decrypted `.tfvars`, API tokens, kubeconfigs, or Talos configs to commits,
  logs, fixtures, or generated artifacts.
- Review a targeted `terraform plan` from the relevant module after controlled
  SOPS decryption. `apply`, server rebuilds, state changes, Flux reconciliation,
  and cluster mutation require explicit operational authorization.
- Preserve the immutable-image and declarative GitOps model. Do not patch a
  live node to compensate for a repository configuration problem.

Before handoff, run the smallest formatting, validation, or plan command that
matches the changed module and include the intended infrastructure effect.

## Two tracks

The repository splits into two tracks with separate guides. Work in the one that
matches the change; everything below this section applies to both.

- **Infrastructure** — platform engineering, Terraform, Talos, Kubernetes, Flux,
  monitoring, storage: `docs/infrastructure/agent-guide.md`. Also the track for
  adding a Grafana dashboard (`infrastructure/monitoring/`).
- **Data platform** — pipelines, Spark jobs, analytics:
  `docs/data-platform/agent-guide.md`. Also the track for scaling Spark
  resources (`PROJECT.yaml` or the Kubernetes manifests).

## GitOps deployment

All production change goes through Git. Infrastructure changes are edits to
manifests under `infrastructure/`, committed, and reconciled by Flux. Data
pipeline changes are edits under `data-platform/projects/`, followed by a Docker
image build and a Kubernetes manifest deploy. Reserve imperative
`kubectl apply` for debugging and testing.

## Encryption

Encrypt before committing, always. That covers `talos/cluster.yaml` (cluster
config, IPs, tokens), `terraform-v2/*.tfvars` (Hetzner API token, credentials),
`infrastructure/storage/s3-secret.yaml` (S3 credentials), and any other file
carrying passwords, keys, addresses, or tokens.

```bash
# Generate the age key (first time only — back it up offline)
age-keygen -o age.key

# Encrypt
sops --encrypt --in-place talos/cluster.yaml
sops --encrypt terraform.tfvars > terraform.tfvars.enc

# Edit in place, decrypting on the fly
export SOPS_AGE_KEY_FILE="$REPO_ROOT"/age.key
sops talos/cluster.yaml

# Pre-commit check
grep -q "sops:" file || echo "ERROR: Not encrypted!"
```

Never commit `age.key`, an unencrypted `terraform.tfvars` (use the `.enc`
version), `config/secrets.yaml`, or any plaintext credential.
`docs/infrastructure/encryption.md` is the complete guide.

## Repository layout

```
datacluster-template/
├── infrastructure/             # Platform: Terraform, K8s, monitoring
│   ├── monitoring/             # Prometheus, Grafana
│   ├── spark-operator/         # Spark Operator deployment
│   └── storage/                # CSI drivers, S3 secrets
│
├── data-platform/              # Data pipelines and analytics code
│   ├── common/                 # Reusable libraries
│   └── projects/               # Independent, self-contained pipelines
│       ├── user_analytics/
│       └── event_streaming/
│
├── terraform-v2/               # Hetzner infrastructure as code
├── talos/                      # Talos OS configuration
├── clusters/                   # Flux GitOps definitions
├── docs/
│   ├── infrastructure/         # Platform docs + agent guide
│   └── data-platform/          # Data pipeline docs + agent guide
└── scripts/                    # Helper scripts
```

## Tooling

Infrastructure work uses `terraform`, `talosctl`, `kubectl`, `flux`, `sops`, and
`helm`. Data platform work uses `spark-submit` for local testing, `pytest`,
`docker`, `kubectl`, and `kustomize` for environment overlays. `sops` and `git`
are common to both, and `sops` is the only sanctioned path for secret material.

## Working with secrets

```bash
# Create
cp config/secrets.yaml.example config/secrets.yaml
vim config/secrets.yaml
sops --encrypt config/secrets.yaml > config/secrets.yaml.enc
git add config/secrets.yaml.enc
echo "config/secrets.yaml" >> .gitignore

# Use in Terraform
export SOPS_AGE_KEY_FILE="$REPO_ROOT"/age.key
cd terraform-v2
sops -d terraform.tfvars.enc > terraform.tfvars
terraform apply
rm terraform.tfvars   # always clean up
```

## Cluster access

Node addresses stay placeholders in a template. In a cluster repository cut from
it, get the real ones from `terraform -chdir=terraform-v2 output
control_plane_public_ips`, or from the decrypted `talosconfig`. Do not paste a
live address back into a tracked file.

```bash
# Kubernetes
export KUBECONFIG="$REPO_ROOT"/clusters/.kube/config
kubectl get nodes

# Talos
export TALOSCONFIG="$REPO_ROOT"/terraform-v2/talosconfig
talosctl -n <CONTROL_PLANE_PUBLIC_IP> version
```

## Test before production

```bash
# Terraform: plan, read the plan, then apply that plan
terraform plan -out=upgrade.tfplan
terraform apply upgrade.tfplan

# Kubernetes: server-side dry run
kubectl apply --dry-run=server -f manifest.yaml

# Data pipelines: tests, then local Spark, then dev before anything else
cd data-platform/projects/my-pipeline/
pytest tests/
spark-submit src/landing.py --config config/environments/dev.yaml
kubectl apply -k k8s/overlays/dev/
```

Promote dev → staging → production, in that order.

## Essential documentation

Infrastructure: `docs/infrastructure/architecture.md`,
`encryption.md`, `hetzner.md`, `talos.md`, `monitoring.md`.

Data platform: `docs/data-platform/project-separation-strategy.md`,
`PROJECT-QUICK-REF.md`, `data-pipeline-strategy.md`.
