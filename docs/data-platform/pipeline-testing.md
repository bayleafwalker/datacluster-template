# Pipeline Deployment & Testing Guide

## Overview
This guide covers building, deploying, and monitoring Spark pipelines on the Datacluster platform.

## Sample Pipelines Created

### 1. User Analytics Batch Job
- **File**: `src/batch_job.py`
- **Purpose**: ETL pipeline demonstrating Extract-Transform-Load pattern
- **Features**:
  - Generates 10,000 sample user events (100 users, 5 event types)
  - Aggregates metrics per user and event type
  - Writes results to Parquet format
  - Demonstrates typical batch processing workflow

### 2. Real-time Event Streaming
- **File**: `src/streaming_job.py`
- **Purpose**: Structured Streaming with windowed aggregations
- **Features**:
  - Rate source generating 10 events/second
  - 1-minute tumbling windows with watermarking
  - Dual sink: console + Parquet
  - Demonstrates streaming state management

## Build & Deploy Workflow

### Step 1: Build Docker Image

```bash
cd /projects/dev/datacluster/src

# Build the image
docker build -t ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-spark:0.1.0 -f Dockerfile .

# Login to GitHub Container Registry (if not already)
echo $GITHUB_TOKEN | docker login ghcr.io -u <YOUR-GITHUB-USERNAME> --password-stdin

# Push the image
docker push ghcr.io/<YOUR-GITHUB-USERNAME>/datacluster-spark:0.1.0
```

**Image Contents**:
- Base: `apache/spark:3.5.0` (official Spark image)
- Python dependencies: pandas, numpy, pyarrow, boto3
- Application code: `batch_job.py`, `streaming_job.py`
- Working directory: `/app`

### Step 2: Deploy SparkApplications

```bash
# Deploy sample pipelines to cluster
kubectl apply -f /projects/dev/datacluster/pipelines/sample-pipelines.yaml

# Verify deployment
kubectl get sparkapplications -n spark-operator
kubectl get pods -n spark-operator
```

**Expected Resources**:
- `user-analytics-batch`: Batch ETL (runs once, completes)
- `realtime-event-streaming`: Streaming job (runs indefinitely)

### Step 3: Monitor Execution

#### CLI Monitoring
```bash
# Watch SparkApplication status
kubectl get sparkapplications -n spark-operator -w

# Check driver logs
kubectl logs -n spark-operator -l spark-role=driver -f

# Check executor logs
kubectl logs -n spark-operator -l spark-role=executor -f --tail=50

# Describe SparkApplication for detailed status
kubectl describe sparkapplication user-analytics-batch -n spark-operator
```

#### Spark UI (Port Forward)
```bash
# Find driver service
kubectl get svc -n spark-operator | grep driver

# Forward Spark UI port (replace with actual driver pod name)
kubectl port-forward -n spark-operator user-analytics-batch-driver 4040:4040

# Open in browser: http://localhost:4040
```

**Spark UI Shows**:
- Stages and tasks execution timeline
- Executor metrics (CPU, memory, shuffle)
- SQL queries and DAG visualization
- Storage and environment details

#### Grafana Dashboard
```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80

# Login: admin / admin (default, CHANGE THIS)
# Navigate to "Datacluster - Spark Workload Overview" dashboard
```

**Dashboard Panels**:
1. **Active Spark Pods**: Count of drivers and executors over time
2. **CPU Usage**: Real-time CPU utilization by role (driver vs executor)
3. **Memory Usage**: Working set bytes for drivers and executors
4. **Task Execution**: Completed and failed tasks per second
5. **Pod Status Table**: All Spark pods with status and node placement
6. **Network Throughput**: RX/TX bytes for data shuffle
7. **Operator Health**: Spark Operator webhook availability

### Step 4: Access Results

#### Local Output (for testing)
```bash
# Batch job output
kubectl exec -n spark-operator user-analytics-batch-driver -- ls -lh /tmp/datacluster-output/

# Copy results locally
kubectl cp spark-operator/user-analytics-batch-driver:/tmp/datacluster-output/user_metrics ./output/

# View Parquet files
python3 -c "import pandas as pd; print(pd.read_parquet('./output/user_metrics'))"
```

#### Production Storage (S3)
For production deployments, configure S3 in SparkApplication:
```yaml
spec:
  hadoopConf:
    "fs.s3a.endpoint": "https://hel1.your-objectstorage.hetzner.com"
    "fs.s3a.access.key": "${S3_ACCESS_KEY}"  # From secret
    "fs.s3a.secret.key": "${S3_SECRET_KEY}"  # From secret
```

Then use S3 paths:
```python
df.write.parquet("s3a://datacluster-spark/curated/user_metrics/")
```

## Cluster Function Assessment

### Health Checks

#### 1. Kubernetes Cluster
```bash
# Node status
kubectl get nodes -o wide

# Expected: 2 nodes (control-1, worker-1) Ready

# Resource availability
kubectl top nodes
kubectl top pods -n spark-operator
```

#### 2. Spark Operator
```bash
# Operator pod
kubectl get pods -n spark-operator -l app.kubernetes.io/name=spark-operator

# Expected: 1 pod Running

# CRD availability
kubectl get crd sparkapplications.sparkoperator.k8s.io

# Webhook health
kubectl get validatingwebhookconfigurations spark-webhook-config
```

#### 3. Monitoring Stack
```bash
# Prometheus/Grafana pods
kubectl get pods -n monitoring

# Expected: prometheus-*, grafana-*, operator-* Running

# ServiceMonitors for Spark
kubectl get servicemonitors -n spark-operator

# Check Prometheus targets
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Open: http://localhost:9090/targets (look for spark-operator endpoints)
```

### Performance Benchmarks

Run the batch job and collect metrics:

```bash
# Deploy batch job
kubectl apply -f pipelines/sample-pipelines.yaml

# Wait for completion
kubectl wait --for=condition=completed sparkapplication/user-analytics-batch -n spark-operator --timeout=600s

# Extract metrics from Spark UI or logs
kubectl logs -n spark-operator user-analytics-batch-driver | grep "Job Summary"
```

**Target Performance** (2-node cluster: CX23 + CX33):
- Batch job (10k events): 30-60 seconds end-to-end
- Streaming throughput: 10 events/sec sustained
- CPU utilization: 30-60% avg per node
- Memory usage: <2GB per executor

### Troubleshooting

#### Pod OOMKilled
```bash
# Symptoms
kubectl get pods -n spark-operator | grep OOMKilled

# Fix: Increase memory in SparkApplication
spec:
  executor:
    memory: "2048m"  # Increase from 1024m
```

#### Driver/Executor Not Scheduling
```bash
# Check pending pods
kubectl get pods -n spark-operator | grep Pending
kubectl describe pod <pod-name> -n spark-operator

# Common issues:
# 1. Insufficient resources → Scale down executor instances
# 2. ImagePullBackOff → Check image name/tag, GHCR authentication
# 3. Volume mount errors → Verify PVC exists
```

#### No Metrics in Grafana
```bash
# Verify ServiceMonitor created
kubectl get servicemonitors -n spark-operator

# Check Prometheus scrape config
kubectl get prometheus -n monitoring kube-prometheus-stack-prometheus -o yaml | grep serviceMonitorSelector

# Ensure SparkApplication has monitoring.prometheus enabled
```

#### Streaming Job Crashes Loop
```bash
# Check logs for errors
kubectl logs -n spark-operator realtime-event-streaming-driver --previous

# Common fixes:
# 1. Checkpoint corruption → Delete checkpoint dir
# 2. Kafka connection issues → Verify Kafka bootstrap servers
# 3. Out of memory → Increase driver/executor memory
```

## Next Steps

### 1. Production Readiness
- [ ] Encrypt S3 credentials with SOPS (see `docs/encryption.md`)
- [ ] Configure Hetzner Object Storage bucket
- [ ] Update SparkApplications to use S3 paths
- [ ] Set up Flux auto-sync for `pipelines/` directory
- [ ] Configure alerting rules in Prometheus

### 2. Custom Pipelines
- [ ] Copy `pipelines/_template.yaml` for new jobs
- [ ] Write PySpark code in `src/your_pipeline.py`
- [ ] Update Dockerfile to include new script
- [ ] Build & push new image tag
- [ ] Deploy via `kubectl apply` or Git commit (Flux)

### 3. Advanced Features
- [ ] Implement Argo Workflows for DAG orchestration
- [ ] Add Kafka integration for streaming sources
- [ ] Configure Delta Lake for ACID transactions
- [ ] Set up Spark History Server for completed jobs
- [ ] Implement data quality checks with Great Expectations

## Cost Optimization Tips

**Current Configuration** (€10/month):
- Control plane: CX23 (2 vCPU, 4GB RAM) - €6.29/mo
- Worker: CX33 (4 vCPU, 8GB RAM) - €13.04/mo
- Total: €19.33/mo (adjust by destroying idle servers)

**Optimization Strategies**:
1. **Destroy worker when idle**: `terraform destroy -target=module.talos.hcloud_server.workers_new`
2. **Scale executors dynamically**: Enable `spark.dynamicAllocation.enabled`
3. **Use spot instances**: Hetzner doesn't offer spots, but recreate servers as needed
4. **Aggressive resource limits**: Set tight CPU/memory limits to pack more pods per node
5. **Schedule batch jobs**: Run ETL during off-peak hours, destroy cluster overnight

## Reference

- **Spark Operator Docs**: https://github.com/kubeflow/spark-operator
- **Spark Configuration**: https://spark.apache.org/docs/latest/configuration.html
- **Grafana Dashboards**: https://grafana.com/grafana/dashboards/
- **Kubernetes Monitoring**: https://prometheus-operator.dev/

---

**Created**: 2025-12-01  
**Cluster**: hetzner-prod (Talos 1.8.3, K8s 1.33.0)  
**Spark Version**: 3.5.0
