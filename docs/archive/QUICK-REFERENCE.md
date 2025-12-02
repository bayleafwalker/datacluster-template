# Quick Reference - Datacluster Pipelines

## ⚠️ CRITICAL: Set Cluster Context First!

```bash
# Always run this before any kubectl commands!
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig

# Or use the helper script:
source scripts/switch-context.sh datacluster

# Verify you're on Hetzner Datacluster (should show control-plane-1, worker-1):
kubectl get nodes
```

## One-Liners

### Deployment
```bash
# Complete deployment (build + push + deploy)
./scripts/deploy-pipelines.sh all

# Deploy only (image already pushed)
kubectl apply -f pipelines/sample-pipelines.yaml
```

### Monitoring
```bash
# Watch SparkApplications
kubectl get sparkapplications -n spark-operator -w

# Stream driver logs
kubectl logs -n spark-operator -l spark-role=driver -f

# Stream executor logs  
kubectl logs -n spark-operator -l spark-role=executor -f --max-log-requests=10

# Check pod status
kubectl get pods -n spark-operator -o wide
```

### Access UIs
```bash
# Grafana (dashboard)
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# → http://localhost:3000 (admin/admin)

# Prometheus (metrics)
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# → http://localhost:9090

# Spark UI (per-job)
kubectl port-forward -n spark-operator <driver-pod-name> 4040:4040
# → http://localhost:4040
```

### Troubleshooting
```bash
# Describe application
kubectl describe sparkapplication <name> -n spark-operator

# Get events
kubectl get events -n spark-operator --sort-by='.lastTimestamp'

# Check why pod is pending
kubectl describe pod <pod-name> -n spark-operator | grep -A 10 Events

# Restart failed job
kubectl delete sparkapplication <name> -n spark-operator
kubectl apply -f pipelines/sample-pipelines.yaml
```

### Resource Management
```bash
# Scale executors (edit manifest)
kubectl edit sparkapplication user-analytics-batch -n spark-operator
# Change: spec.executor.instances: 4

# Delete all Spark resources
kubectl delete sparkapplications --all -n spark-operator

# Check resource usage
kubectl top nodes
kubectl top pods -n spark-operator
```

## File Locations

| Component | Path |
|-----------|------|
| Batch job code | `src/batch_job.py` |
| Streaming job code | `src/streaming_job.py` |
| Dockerfile | `src/Dockerfile` |
| SparkApplications | `pipelines/sample-pipelines.yaml` |
| Template | `pipelines/_template.yaml` |
| Deployment script | `scripts/deploy-pipelines.sh` |
| Grafana dashboard | `infrastructure/monitoring/grafana-dashboards/spark-workload.json` |
| Spark Operator config | `infrastructure/spark-operator/release.yaml` |
| Documentation | `docs/pipeline-testing.md`, `docs/visualization-plan.md` |

## Common PromQL Queries

```promql
# Active drivers
count(kube_pod_info{namespace="spark-operator", pod=~".*-driver"})

# Active executors
count(kube_pod_info{namespace="spark-operator", pod=~".*-exec-.*"})

# Driver CPU usage (%)
avg(rate(container_cpu_usage_seconds_total{namespace="spark-operator", pod=~".*-driver"}[5m])) * 100

# Executor memory (GB)
sum(container_memory_working_set_bytes{namespace="spark-operator", pod=~".*-exec-.*"}) / 1024^3

# Completed tasks per second
sum(rate(metrics_executor_completedTasks_total[5m]))

# Failed task ratio
rate(metrics_executor_failedTasks_total[5m]) / rate(metrics_executor_completedTasks_total[5m])
```

## Pipeline Lifecycle

```
1. WRITE CODE     → src/my_pipeline.py
2. UPDATE DOCKER  → src/Dockerfile (add COPY line)
3. BUILD IMAGE    → docker build -t <image>:<tag> .
4. PUSH IMAGE     → docker push <image>:<tag>
5. CREATE YAML    → Copy pipelines/_template.yaml
6. EDIT MANIFEST  → Update image, mainApplicationFile, resources
7. APPLY          → kubectl apply -f pipelines/my-pipeline.yaml
8. MONITOR        → kubectl logs -f, Grafana, Spark UI
```

## Namespace Mapping

| Resource Type | Namespace |
|---------------|-----------|
| SparkApplications | `spark-operator` |
| Monitoring (Prometheus/Grafana) | `kube-prometheus-stack` |
| Flux GitOps | `flux-system` |
| Storage (Longhorn) | `longhorn-system` |

## Key Metrics

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| CPU Usage | <60% | 60-80% | >80% |
| Memory Usage | <70% | 70-85% | >85% |
| Failed Task Ratio | <1% | 1-5% | >5% |
| Driver Restarts | 0 | 1-2 | >3 |
| Pod Pending Time | <30s | 30-120s | >2min |

## Default Resource Limits

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| Driver | 500m | 1200m | 1Gi | 1Gi |
| Executor | 500m | 1500m | 1Gi | 2Gi |
| Spark Operator | 100m | 200m | 128Mi | 256Mi |

## Alert Thresholds

```yaml
# High executor failure rate
rate(metrics_executor_failedTasks_total[5m]) / rate(metrics_executor_completedTasks_total[5m]) > 0.05

# Spark Operator down
up{job="spark-operator-webhook"} == 0

# Driver OOMKilled
kube_pod_container_status_last_terminated_reason{reason="OOMKilled", namespace="spark-operator"} == 1

# Too many executors
count(kube_pod_info{namespace="spark-operator", pod=~".*-exec-.*"}) > 10
```

## Environment Variables

```bash
# For deploy script
export IMAGE_NAME="ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-spark"
export IMAGE_TAG="0.1.0"
export NAMESPACE="spark-operator"

# For SOPS encryption
export SOPS_AGE_KEY_FILE=/projects/dev/datacluster/age.key

# For kubectl
export KUBECONFIG=/projects/dev/datacluster/terraform-v2/kubeconfig

# For Talos
export TALOSCONFIG=/projects/dev/datacluster/terraform-v2/talosconfig
```

## Cost Breakdown (Monthly)

| Component | Cost (€) | Notes |
|-----------|----------|-------|
| CX23 control-plane | 6.29 | Always on |
| CX33 worker | 13.04 | Can destroy when idle |
| Prometheus PV (20GB) | 1.20 | Persistent |
| Grafana PV (5GB) | 0.30 | Persistent |
| **Total (active)** | **20.83** | Full cluster |
| **Total (idle)** | **7.79** | Worker destroyed |

## Handy Aliases

Add to `~/.bashrc`:

```bash
alias k='kubectl'
alias ksp='kubectl -n spark-operator'
alias kmon='kubectl -n kube-prometheus-stack'
alias klogs='kubectl logs -n spark-operator -l spark-role=driver -f'
alias kpods='kubectl get pods -n spark-operator -o wide'
alias kspark='kubectl get sparkapplications -n spark-operator'
alias sparkui='kubectl port-forward -n spark-operator $(kubectl get pods -n spark-operator -l spark-role=driver -o name | head -1) 4040:4040'
alias grafana='kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80'
```

## Links

- **GitHub Repo**: (your repository URL)
- **Spark Operator**: https://github.com/kubeflow/spark-operator
- **Spark Docs**: https://spark.apache.org/docs/latest/
- **Grafana Docs**: https://grafana.com/docs/
- **Prometheus Docs**: https://prometheus.io/docs/

---

**Last Updated**: 2025-12-01  
**Keep this file handy for daily operations!**
