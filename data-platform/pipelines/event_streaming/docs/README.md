# Event Streaming Pipeline

## Status: ✅ Migrated from `src/streaming_job.py`

### Overview
Real-time streaming pipeline that processes events with windowed aggregations.

### What Changed in Migration
- ✅ Uses standard logging
- ✅ Follows new project structure
- ✅ Moved to `data-platform/pipelines/event_streaming/`
- ✅ Ready for Kafka integration (currently uses rate source)

### Data Flow
```
Rate Source → Window Aggregation (1 min) → Console + Parquet Sink
```

### Outputs
- Console: Real-time progress
- `/tmp/datacluster-output/streaming_events/`: Parquet files

### Running

**Locally:**
```bash
cd data-platform
spark-submit --master local[*] pipelines/event_streaming/src/streaming_pipeline.py
```

**On Cluster:**
```bash
kubectl apply -f pipelines/event_streaming/k8s/streaming.yaml
```

### Future Enhancements
- Replace rate source with Kafka connector
- Add Delta Lake for streaming writes
- Implement complex event processing

### Original Code
See `src/streaming_job.py` (deprecated) for original implementation.

---
**Migrated**: 2025-12-02  
**Status**: Production-ready
