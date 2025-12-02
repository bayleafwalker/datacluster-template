# Datacluster Deployment Guide - Hetzner Cloud

**Cluster**: Fresh Talos deployment on Hetzner Cloud  
**Nodes**: control-plane-1 (CX23) + worker-1 (CX33)  
**Status**: Infrastructure not yet deployed

---

## ⚠️ Important: Cluster Context

This project has **TWO separate clusters**:
1. **Homelab cluster** (admin@main): Private appservice cluster for homelab services
2. **Datacluster** (admin@datacluster): Public Hetzner Cloud cluster for data services

**Always set the correct context before operations:**

```bash
# Set Datacluster context (REQUIRED for all commands below)
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig

# Verify you're on the right cluster
kubectl config current-context
# Should show: admin@datacluster

kubectl get nodes
# Should show: control-plane-1, worker-1
```

---

## Quick Start: Manual Deployment

This is the fastest path to get pipelines running.

### Step 1: Deploy Infrastructure (20 minutes)

```bash
# Set context
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig

# Navigate to project
cd /projects/dev/datacluster

# Create namespaces
kubectl create namespace spark-operator
kubectl create namespace monitoring

# Deploy monitoring stack (Prometheus + Grafana)
kubectl apply -f infrastructure/monitoring/namespace.yaml
kubectl apply -f infrastructure/monitoring/release.yaml

# Deploy Spark Operator
kubectl apply -f infrastructure/spark-operator/namespace.yaml
kubectl apply -f infrastructure/spark-operator/release.yaml

# Wait for Helm operators to deploy releases (this may take 5-10 minutes)
echo "Waiting for monitoring stack..."
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=kube-prometheus-stack-operator \
  -n monitoring \
  --timeout=600s

echo "Waiting for Spark Operator..."
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=spark-operator \
  -n spark-operator \
  --timeout=600s

# Verify deployment
kubectl get pods -n monitoring
kubectl get pods -n spark-operator
```

**Expected Outcome**:
- Prometheus, Grafana, and related pods running in `monitoring` namespace
- Spark Operator pod running in `spark-operator` namespace

### Step 2: Build & Push Spark Image (15 minutes)

```bash
# Login to GitHub Container Registry
export GITHUB_TOKEN="<your_personal_access_token>"
echo $GITHUB_TOKEN | docker login ghcr.io -u <YOUR-GITHUB-USERNAME> --password-stdin

# Build image
cd /projects/dev/datacluster
docker build -t ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-spark:0.1.0 -f src/Dockerfile src/

# Push to registry
docker push ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-spark:0.1.0

# Verify
docker images | grep datacluster-spark
```

**Note**: If you don't have a GitHub token, create one at:
https://github.com/settings/tokens/new (select `write:packages` scope)

### Step 3: Deploy Sample Pipelines (5 minutes)

```bash
# Ensure correct context
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig

# Deploy SparkApplications
kubectl apply -f pipelines/sample-pipelines.yaml

# Watch deployment
kubectl get sparkapplications -n spark-operator -w
# Press Ctrl+C to exit

# Check pods
kubectl get pods -n spark-operator
```

**Expected Outcome**:
- `user-analytics-batch-driver` pod (batch job - completes in 1-2 min)
- `realtime-event-streaming-driver` pod (streaming - runs indefinitely)
- 2-4 executor pods per application

### Step 4: Monitor & Verify (10 minutes)

```bash
# Stream batch job logs
kubectl logs -n spark-operator -l spark-role=driver,spark-app-name=user-analytics-batch -f

# Expected output:
# === Starting User Analytics Batch Job ===
# EXTRACT: Generating sample data...
# Generated 10000 events
# TRANSFORM: Aggregating user metrics...
# LOAD: Writing results to storage...
# === Job Completed Successfully ===

# Check streaming job
kubectl logs -n spark-operator -l spark-role=driver,spark-app-name=realtime-event-streaming -f --tail=50

# Access Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# Open: http://localhost:3000 (login: admin/admin)
# Import dashboard: infrastructure/monitoring/grafana-dashboards/spark-workload.json

# Access Spark UI (for any running job)
export DRIVER_POD=$(kubectl get pods -n spark-operator -l spark-role=driver -o name | head -1)
kubectl port-forward -n spark-operator $DRIVER_POD 4040:4040
# Open: http://localhost:4040
```

---

## Alternative: GitOps Deployment (Recommended for Production)

Bootstrap Flux for automated deployment and management.

### Step 1: Bootstrap Flux

```bash
# Set context
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig

# Export GitHub credentials
export GITHUB_TOKEN="<your_token>"
export GITHUB_USER="<YOUR-GITHUB-USERNAME>"

# Bootstrap Flux
flux bootstrap github \
  --owner=$GITHUB_USER \
  --repository=datacluster \
  --branch=main \
  --path=clusters/hetzner-prod \
  --personal

# Wait for Flux to deploy
flux get kustomizations --watch
```

### Step 2: Infrastructure Auto-Deploys

Flux will automatically apply all manifests in `infrastructure/`:
- Monitoring stack (Prometheus, Grafana)
- Spark Operator
- Storage configurations

Monitor progress:
```bash
kubectl get kustomizations -n flux-system
kubectl get helmreleases -n monitoring
kubectl get helmreleases -n spark-operator
```

### Step 3: Deploy Pipelines

After infrastructure is ready, follow Steps 2-4 from the manual deployment guide above.

---

## Troubleshooting

### "No resources found" in monitoring/spark-operator

**Cause**: HelmRelease hasn't deployed the chart yet

**Fix**:
```bash
# Check HelmRelease status
kubectl get helmreleases -A

# Describe to see errors
kubectl describe helmrelease kube-prometheus-stack -n monitoring
kubectl describe helmrelease spark-operator -n spark-operator

# Common issues:
# 1. HelmRepository not ready → Wait for internet connectivity
# 2. Chart version not found → Check version in release.yaml
# 3. Values invalid → Check YAML syntax
```

### "ImagePullBackOff" for Spark pods

**Cause**: Docker image not pushed or authentication issue

**Fix**:
```bash
# Verify image exists
docker images | grep datacluster-spark

# Try pulling manually
docker pull ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-spark:0.1.0

# If private, create image pull secret:
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<YOUR-GITHUB-USERNAME> \
  --docker-password=$GITHUB_TOKEN \
  -n spark-operator

# Update SparkApplication to use secret (add to spec:)
# imagePullSecrets:
#   - ghcr-secret
```

### Pods stuck in "Pending"

**Cause**: Insufficient resources or node selector mismatch

**Fix**:
```bash
# Check why pending
kubectl describe pod <pod-name> -n spark-operator

# View resource usage
kubectl top nodes
kubectl describe node worker-1

# Common solutions:
# 1. Reduce executor instances in SparkApplication
# 2. Lower memory/CPU requests
# 3. Delete other workloads to free resources
```

### "error: the server doesn't have a resource type"

**Cause**: CRD not installed yet (HelmRelease still deploying)

**Fix**: Wait 2-5 minutes for Helm charts to complete, then retry

---

## Verification Checklist

After deployment, verify everything works:

- [ ] Cluster context is `admin@datacluster`
- [ ] 2 nodes show Ready: `kubectl get nodes`
- [ ] Monitoring pods running: `kubectl get pods -n monitoring`
- [ ] Spark Operator running: `kubectl get pods -n spark-operator`
- [ ] ServiceMonitor CRD exists: `kubectl get crd servicemonitors.monitoring.coreos.com`
- [ ] SparkApplication CRD exists: `kubectl get crd sparkapplications.sparkoperator.k8s.io`
- [ ] Batch job completes successfully
- [ ] Streaming job runs continuously
- [ ] Grafana accessible and shows data
- [ ] Spark UI accessible for running jobs

---

## Next Steps After Deployment

1. **Configure S3 Storage** (for production data):
   - Edit `infrastructure/storage/s3-secret.yaml`
   - Add Hetzner Object Storage credentials (SOPS-encrypted)
   - Update SparkApplications to use `s3a://` paths

2. **Set Up Alerting**:
   - Create PrometheusRules in `infrastructure/monitoring/`
   - Configure alert receivers (Slack, email, etc.)

3. **Create Custom Pipelines**:
   - Copy `pipelines/_template.yaml`
   - Write PySpark code in `src/your_pipeline.py`
   - Build new image tag and deploy

4. **Enable Auto-Scaling** (optional):
   - Configure Spark dynamic allocation
   - Set up Kubernetes HPA for executors

5. **Optimize Costs**:
   - Destroy worker node when idle: `terraform destroy -target=...`
   - Schedule batch jobs during off-peak hours
   - Implement spot instance strategies (when Hetzner supports)

---

## Useful Commands

```bash
# Always start with this!
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig

# Quick status check
kubectl get nodes && kubectl get pods -A | grep -E "spark|monitoring"

# Watch all Spark pods
kubectl get pods -n spark-operator -w

# Stream all driver logs
kubectl logs -n spark-operator -l spark-role=driver -f --max-log-requests=5

# Delete and redeploy pipeline
kubectl delete sparkapplication user-analytics-batch -n spark-operator
kubectl apply -f pipelines/sample-pipelines.yaml

# Emergency: Delete all Spark resources
kubectl delete sparkapplications --all -n spark-operator
kubectl delete pods --all -n spark-operator
```

---

**Last Updated**: 2025-12-01  
**Cluster**: Hetzner Cloud Datacluster  
**Contact**: (your contact info)
