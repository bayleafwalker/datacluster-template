# Operations Runbook

## Deployment

### Initial Deployment

```bash
# 1. Build Docker image
cd data-platform
docker build -t ghcr.io/<user>/datacluster-data:<version> -f Dockerfile .
docker push ghcr.io/<user>/datacluster-data:<version>

# 2. Update image tag in k8s manifests
# Edit k8s/landing.yaml, k8s/transform.yaml, k8s/integration.yaml

# 3. Apply to cluster
kubectl apply -f k8s/

# 4. Verify deployment
kubectl get sparkapplications -n spark-operator
kubectl logs -n spark-operator -l spark-app-name=<pipeline-name>-landing -f
```

### Updates

```bash
# 1. Make code changes in src/
# 2. Run tests
pytest tests/ -v

# 3. Build and push new version
docker build -t ghcr.io/<user>/datacluster-data:<new-version> .
docker push ghcr.io/<user>/datacluster-data:<new-version>

# 4. Update k8s manifests with new image tag
# 5. Apply changes
kubectl apply -f k8s/

# 6. Monitor rollout
kubectl get sparkapplications -n spark-operator -w
```

### Rollback

```bash
# 1. Identify last working version
kubectl get sparkapplication <name> -n spark-operator -o yaml | grep image:

# 2. Revert to previous image
kubectl edit sparkapplication <name> -n spark-operator
# Change spec.image to previous version

# 3. Verify
kubectl logs -n spark-operator -l spark-app-name=<name> --tail=100
```

## Monitoring

### Key Dashboards

1. **Grafana - Pipeline Overview**
   - URL: http://grafana/d/pipeline-xyz
   - Metrics: Throughput, latency, errors, resource usage

2. **Spark UI**
   ```bash
   export DRIVER_POD=$(kubectl get pods -n spark-operator \
     -l spark-app-name=<name>-landing,spark-role=driver -o name)
   kubectl port-forward -n spark-operator $DRIVER_POD 4040:4040
   # Open: http://localhost:4040
   ```

3. **Prometheus Queries**
   ```promql
   # Processing rate
   rate(pipeline_records_processed_total{pipeline="<name>"}[5m])
   
   # Latency
   pipeline_latency_seconds{pipeline="<name>"}
   
   # Error rate
   rate(pipeline_errors_total{pipeline="<name>"}[5m])
   ```

### Health Checks

```bash
# Check SparkApplication status
kubectl get sparkapplication <name> -n spark-operator

# Check pod status
kubectl get pods -n spark-operator -l spark-app-name=<name>

# View recent logs
kubectl logs -n spark-operator -l spark-app-name=<name> --tail=100

# Check data output
aws s3 ls s3://datacluster-curated/<output-path>/ --recursive | tail -20
```

## Troubleshooting

### Issue: Pipeline Not Starting

**Symptoms**: SparkApplication stuck in "SUBMITTED" state

**Diagnosis**:
```bash
kubectl describe sparkapplication <name> -n spark-operator
kubectl get pods -n spark-operator -l spark-app-name=<name>
```

**Common Causes**:
1. Image pull failure
   - **Fix**: Verify image exists and registry credentials are correct
2. Insufficient resources
   - **Fix**: Scale down other workloads or increase cluster capacity
3. Volume mount issues
   - **Fix**: Check PVC exists: `kubectl get pvc -n spark-operator`

### Issue: High Latency

**Symptoms**: Pipeline takes >SLA time to complete

**Diagnosis**:
```bash
# Check Spark stages
# Access Spark UI (see Monitoring section)

# Check resource usage
kubectl top pods -n spark-operator -l spark-app-name=<name>

# Check data volume
# Verify input data size hasn't grown unexpectedly
```

**Solutions**:
1. Increase executor instances in `k8s/<stage>.yaml`
2. Increase executor memory
3. Optimize Spark configuration (shuffle partitions, memory fraction)
4. Partition data more granularly

### Issue: Data Quality Failures

**Symptoms**: `pipeline_quality_violations_total` increasing

**Diagnosis**:
```bash
# View driver logs for quality check failures
kubectl logs -n spark-operator <driver-pod> | grep -i "quality\|validation"

# Query output data
spark-submit --master k8s://... validate_output.py
```

**Solutions**:
1. Check upstream data sources for schema changes
2. Review and update quality check thresholds
3. Implement additional validation rules
4. Contact upstream team if data corruption detected

### Issue: OOMKilled Executors

**Symptoms**: Executors crash with exit code 137

**Diagnosis**:
```bash
kubectl describe pod <executor-pod> -n spark-operator
# Look for "Reason: OOMKilled"
```

**Solutions**:
1. Increase `spec.executor.memory` in SparkApplication
2. Reduce `spark.executor.cores` to allocate more memory per core
3. Enable executor memory overhead:
   ```yaml
   sparkConf:
     "spark.executor.memoryOverhead": "1024m"
   ```
4. Reduce data shuffle size (repartition earlier)

### Issue: Missing Output Data

**Symptoms**: Expected output files not in S3

**Diagnosis**:
```bash
# Check if pipeline completed successfully
kubectl get sparkapplication <name> -n spark-operator
# Look for "COMPLETED" status

# Check logs for errors
kubectl logs -n spark-operator <driver-pod> | grep -i "error\|exception"

# Verify S3 path
aws s3 ls s3://datacluster-curated/<expected-path>/
```

**Solutions**:
1. Pipeline failed silently - check logs for exceptions
2. Wrong output path - verify configuration
3. S3 credentials issue - check `s3-credentials` secret
4. Permissions issue - verify IAM policy

### Issue: Duplicate Records

**Symptoms**: Data contains duplicate keys

**Diagnosis**:
```bash
# Run duplicate check query
spark-submit --master k8s://... check_duplicates.py \
  --path s3://datacluster-curated/<path> \
  --keys user_id,date
```

**Solutions**:
1. Add deduplication step in transform stage:
   ```python
   from data_platform.common.transforms.deduplication import Deduplicator
   df = Deduplicator.keep_latest(df, ["user_id"], "timestamp")
   ```
2. Fix upstream source to prevent duplicates
3. Use Delta Lake UPSERT instead of append

## Performance Tuning

### Current Configuration
- Driver: X cores, Y GB memory
- Executor: X cores, Y GB memory, Z instances
- Shuffle partitions: N

### Tuning Guide

**For larger datasets**:
```yaml
spec:
  driver:
    cores: 2
    memory: "4096m"
  executor:
    cores: 2
    instances: 6
    memory: "4096m"
  sparkConf:
    "spark.sql.shuffle.partitions": "200"
```

**For streaming jobs**:
```yaml
sparkConf:
  "spark.sql.streaming.checkpointInterval": "10 seconds"
  "spark.streaming.backpressure.enabled": "true"
```

## Emergency Procedures

### Data Quality Incident

1. **Immediate**: Stop pipeline to prevent bad data propagation
   ```bash
   kubectl delete sparkapplication <name> -n spark-operator
   ```

2. **Assess**: Determine extent of bad data
   ```bash
   # Query affected partitions
   # Check when quality degradation started
   ```

3. **Remediate**:
   - Fix data quality issue (code or config)
   - Reprocess affected partitions
   - Validate output before resuming

4. **Communicate**: Notify downstream consumers

### Pipeline Stuck/Hanging

1. **Force kill**:
   ```bash
   kubectl delete sparkapplication <name> -n spark-operator --grace-period=0
   kubectl delete pods -n spark-operator -l spark-app-name=<name>
   ```

2. **Check for resource deadlock**
3. **Restart** with adjusted configuration

### Data Loss Prevention

**Backups**:
- Landing data retained for 7 days (lifecycle policy)
- Curated data retained for 365 days
- Streaming checkpoints backed up hourly

**Recovery**:
```bash
# Restore from specific date
spark-submit reprocess.py --date 2025-12-01 --source landing --dest curated
```

## Maintenance

### Weekly
- Review monitoring dashboards
- Check storage usage trends
- Review error logs

### Monthly
- Optimize Delta tables:
  ```bash
  spark-submit optimize_delta.py --table <path>
  ```
- Vacuum old versions:
  ```bash
  spark-submit vacuum_delta.py --table <path> --retention 168
  ```
- Update dependencies (if needed)

### Quarterly
- Review and update SLAs
- Performance benchmarking
- Disaster recovery drill

## Contacts

- **On-call**: Slack #data-ops
- **Team Lead**: @username
- **Escalation**: manager@example.com

---

**Last Updated**: YYYY-MM-DD  
**Version**: v1.0
