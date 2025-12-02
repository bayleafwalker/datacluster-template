# User Analytics Pipeline

## Status: ✅ Migrated from `src/batch_job.py`

### Overview
Batch ETL pipeline that processes user events and generates analytics metrics.

### What Changed in Migration
- ✅ Uses `data_platform.common.connectors.s3.S3Writer` for output
- ✅ Uses `data_platform.common.transforms.quality.DataQualityChecker` for validation
- ✅ Follows standard logging patterns
- ✅ Moved to `data-platform/pipelines/user_analytics/`

### Data Flow
```
Generate Sample Data → Validate → Transform (Aggregate) → Write Parquet
```

### Outputs
- `user_metrics/`: Per-user aggregations
- `event_metrics/`: Per-event-type aggregations
- `raw_events/`: Partitioned raw data

### Running

**Locally:**
```bash
cd data-platform
spark-submit --master local[*] pipelines/user_analytics/src/batch_pipeline.py
```

**On Cluster:**
```bash
kubectl apply -f pipelines/user_analytics/k8s/batch.yaml
```

### Original Code
See `src/batch_job.py` (deprecated) for original implementation.

---
**Migrated**: 2025-12-02  
**Status**: Production-ready
