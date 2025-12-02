# Talos & Talhelper Automation

This folder uses **talhelper** to generate Talos OS configuration for the `datacluster` Kubernetes cluster.

## Prerequisites

1. Install `talhelper`  
   ```bash
   go install github.com/budimanjojo/talhelper@latest
   ```
2. Install `talosctl` matching `talosVersion` in *cluster.yaml*  
   ```bash
   curl -L https://github.com/siderolabs/talos/releases/download/v1.7.2/talosctl-linux-amd64      -o /usr/local/bin/talosctl && chmod +x /usr/local/bin/talosctl
   ```

## Generate configs

```bash
talhelper genconfig -o generated talos/cluster.yaml
# => generated/controlplane.yaml, generated/worker-*.yaml, generated/talosconfig
```

## Apply configs to nodes

```bash
# Example: apply control-plane config (node must be in maintenance mode)
talosctl apply-config --insecure --nodes <CTRL_IP> --file generated/controlplane.yaml
# bootstrap etcd / control plane
talosctl bootstrap --nodes <CTRL_IP>

# Apply worker configs
for ip in <WORKER_IPS>; do
  talosctl apply-config --insecure --nodes $ip --file generated/${ip}.yaml
done
```

## Continuous upgrades

* Generate new configs after editing *cluster.yaml*  
  `talhelper genconfig -o generated talos/cluster.yaml`
* Apply with `talosctl patch` or `talosctl upgrade`.

> Consider encrypting `cluster.yaml` with **SOPS** since it can hold secrets.
