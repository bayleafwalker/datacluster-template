# Example Pipelines

## 1. Batch ETL

*File:* `pipelines/batch-job.yaml`  
*Code:* `src/batch_job.py`

| Stage | Action |
|-------|--------|
|Extract|Read `users.csv` from NFS `/data/raw/` or `s3a://datacluster/raw/`|
|Transform|Clean nulls, join reference data, run SQL aggregation|
|Load|Write Parquet to `s3a://datacluster/curated/users_daily/`|

Executed with:

```bash
kubectl apply -f pipelines/batch-job.yaml
```

or automatically when Flux syncs.

## 2. Streaming

*File:* `pipelines/streaming-job.yaml`  
*Code:* `src/streaming_job.py`

| Stage | Action |
|-------|--------|
|Source|Spark *rate* stream (10 rows/s) or Kafka topic `events`|
|Process|Windowed count (1 min) + watermarking|
|Sink|Append to `/data/checkpoints/events/` and `/data/output/events_parquet/`|

Runs indefinitely; restart policy `OnFailure`.

---

## Adding a new pipeline

1. Write PySpark script inside `src/`.  
2. Build & push a new Docker tag.  
3. Copy `pipelines/_template.yaml`, edit image & main file, commit.  
4. Flux deploys; monitor with `kubectl get sparkapplications`.

Workflows (Argo) can chain multiple Spark jobs:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: nightly-etl
spec:
  entrypoint: etl
  templates:
    - name: etl
      dag:
        tasks:
          - name: batch
            spark:
              sparkApplicationRef:
                name: batch-job
          - name: compress
            dependencies: [batch]
            container:
              image: alpine
              command: ["tar","czf","/out/archive.tgz","/data/output"]
```
