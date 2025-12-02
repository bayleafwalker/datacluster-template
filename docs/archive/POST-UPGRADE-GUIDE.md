# Post-Upgrade Deployment Guide

## ✅ Completed

### Infrastructure Upgrade
- **Kubernetes**: v1.30.3 → **v1.32.1** ✅
- **Cilium CNI**: v1.16.5 → **v1.17.0** ✅
- **Talos OS**: v1.8.4 (functional, K8s v1.32.1 compatible)
- **Cluster Status**: Both nodes `Ready`, all system pods running

### Configuration
- **Kubeconfig**: Located at `clusters/.kube/config`
- **Talosconfig**: Located at `terraform-v2/talosconfig`
- **Control Plane**: <CONTROL_PLANE_PUBLIC_IP>
- **Worker**: <WORKER_PUBLIC_IP>

## 📋 Remaining Tasks

### 1. Deploy Monitoring Stack

The monitoring stack (Prometheus + Grafana) requires manual Helm installation since Flux GitOps is not yet deployed.

```bash
# Set kubeconfig
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config

# Install kube-prometheus-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=7d \
  --set prometheus.prometheusSpec.resources.requests.cpu=200m \
  --set prometheus.prometheusSpec.resources.requests.memory=512Mi \
  --set grafana.adminPassword=admin \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=5Gi \
  --set alertmanager.enabled=false \
  --set kubeApiServer.enabled=false \
  --set kubeControllerManager.enabled=false \
  --set kubeScheduler.enabled=false \
  --set kubeEtcd.enabled=false

# Wait for pods to be ready (3-5 minutes)
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=5m
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=5m

# Access Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring
# Open http://localhost:3000 (admin/admin)
```

### 2. Deploy Spark Operator

```bash
# Add Spark Operator Helm repo
helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update

# Install Spark Operator
helm install spark-operator spark-operator/spark-operator \
  --namespace spark-operator \
  --create-namespace \
  --set webhook.enable=true \
  --set sparkJobNamespace=default \
  --set image.tag=v1beta2-1.4.3-3.5.0

# Verify installation
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=spark-operator -n spark-operator --timeout=3m
kubectl get pods -n spark-operator
```

### 3. Build and Push Spark Docker Image

```bash
# Build Spark application image
cd /projects/dev/datacluster/src
docker build -t ghcr.io/YOUR_USERNAME/datacluster-spark:0.1.0 .

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Push image
docker push ghcr.io/YOUR_USERNAME/datacluster-spark:0.1.0
```

**Update pipelines**: Edit `pipelines/sample-pipelines.yaml` and replace `ghcr.io/<user>/datacluster-spark:0.1.0` with your actual image URI.

### 4. Deploy Sample Pipelines

```bash
# Deploy SparkApplications
kubectl apply -f pipelines/sample-pipelines.yaml

# Monitor pipeline execution
kubectl get sparkapplications
kubectl get pods -l spark-role=driver

# View batch job logs
kubectl logs -f batch-user-analytics-driver -c spark-kubernetes-driver

# View streaming job logs
kubectl logs -f streaming-event-processor-driver -c spark-kubernetes-driver

# Access Spark UI (while job is running)
kubectl port-forward batch-user-analytics-driver 4040:4040
# Open http://localhost:4040
```

### 5. Import Spark Dashboard to Grafana

```bash
# Port-forward Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring

# In browser:
# 1. Go to http://localhost:3000 (login: admin/admin)
# 2. Navigate to Dashboards → Import
# 3. Upload file: infrastructure/monitoring/grafana-dashboards/spark-workload.json
# 4. Select Prometheus datasource
# 5. Click Import
```

The dashboard includes 7 panels:
- Active Spark Pods (by application)
- CPU Usage per Application
- Memory Usage per Application  
- Task Execution Duration
- Active Pods Table (detailed)
- Network Throughput
- Spark Operator Health

## 🔄 Optional: Deploy Flux GitOps

If you want infrastructure-as-code reconciliation:

```bash
# Install Flux CLI
curl -s https://fluxcd.io/install.sh | sudo bash

# Bootstrap Flux (requires GitHub token)
export GITHUB_TOKEN=<your-token>
flux bootstrap github \
  --owner=YOUR_USERNAME \
  --repository=datacluster \
  --path=clusters/hetzner-prod \
  --personal

# Verify Flux controllers
kubectl get pods -n flux-system
```

Once Flux is running, the HelmRelease manifests in `infrastructure/` will automatically deploy/update.

## 🚀 Quick Verification Commands

```bash
# Cluster health
export KUBECONFIG=/projects/dev/datacluster/clusters/.kube/config
kubectl get nodes -o wide
kubectl get pods -A

# Talos version
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
talosctl version --nodes <CONTROL_PLANE_PUBLIC_IP>

# Check SparkApplications
kubectl get sparkapplications
kubectl describe sparkapplication batch-user-analytics

# Check monitoring
kubectl get pods -n monitoring
kubectl get pvc -n monitoring

# Resource usage
kubectl top nodes
kubectl top pods -A
```

## 📊 Cost Breakdown (Current)

| Component | Type | Monthly Cost |
|-----------|------|--------------|
| control-plane-1 | CX23 | €3.75 |
| worker-1 | CX33 | €6.26 |
| Public IPv4 (x2) | Primary IPs | €1.26 |
| **Total** | | **€11.27/month** |

Volumes are billed separately when created (€0.11/GB/month for Hetzner Volumes).

## 🛡️ Security Notes

1. **Change Grafana password**: Default is `admin/admin`
   ```bash
   kubectl exec -it -n monitoring deployment/kube-prometheus-stack-grafana -- grafana-cli admin reset-admin-password NEW_PASSWORD
   ```

2. **SOPS-encrypt credentials**: Any secrets should be encrypted before committing:
   ```bash
   export SOPS_AGE_KEY_FILE=/projects/dev/datacluster/age.key
   sops --encrypt --in-place infrastructure/storage/s3-secret.yaml
   ```

3. **Network policies**: Consider adding NetworkPolicies to restrict traffic between namespaces

## 🔧 Troubleshooting

### Pods Pending (Storage Issues)
```bash
# Check if hcloud-volumes StorageClass exists
kubectl get storageclass

# If missing, the Hetzner CSI driver may not be installed
# (Usually auto-installed by hcloud-talos module)
```

### Spark Jobs Failing
```bash
# Check Spark Operator logs
kubectl logs -n spark-operator deployment/spark-operator

# Check driver pod events
kubectl describe pod <driver-pod-name>

# Verify RBAC permissions
kubectl get serviceaccount spark -o yaml
```

### Cannot Access Grafana
```bash
# Check if Grafana pod is running
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana

# Check logs
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana

# Restart if needed
kubectl rollout restart deployment/kube-prometheus-stack-grafana -n monitoring
```

## 📚 Reference Documentation

- [docs/upgrade-guide.md](docs/upgrade-guide.md) - Talos/K8s upgrade procedures
- [UPGRADE-STATUS.md](UPGRADE-STATUS.md) - Current cluster state and decisions
- [docs/pipelines.md](docs/pipelines.md) - Spark pipeline development guide
- [docs/monitoring.md](docs/monitoring.md) - Monitoring architecture
- [QUICK-REFERENCE.md](QUICK-REFERENCE.md) - Daily operations cheatsheet

## 🎯 Success Criteria

You'll know everything is working when:

- ✅ `kubectl get nodes` shows 2 nodes `Ready` with v1.32.1
- ✅ `kubectl get pods -A` shows all pods `Running` (no CrashLoopBackOff)
- ✅ Grafana dashboard loads at http://localhost:3000
- ✅ `kubectl get sparkapplications` shows batch job `COMPLETED` and streaming job `RUNNING`
- ✅ Spark dashboard in Grafana displays metrics
- ✅ `kubectl top nodes` shows <60% CPU usage on control plane
