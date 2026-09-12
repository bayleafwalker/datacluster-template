# Data Platform Projects

This directory contains independent, self-contained data pipeline projects.

## 🎯 Project Organization

Each project follows a standard structure and contains everything needed to develop, test, and deploy:

- `PROJECT.yaml` - Single source of truth (metadata, resources, schedule, SLAs)
- `config/` - All configuration centralized (pipeline, spark, storage, secrets)
- `schemas/` - Avro schemas for input/output data
- `src/` - Source code (landing, transform, integration stages)
- `tests/` - Unit/integration tests + test data generators
- `k8s/` - Kubernetes manifests (base + overlays for dev/staging/prod)
- `docs/` - Complete documentation (README, architecture, runbook)
- `scripts/` - Project-specific automation

## 📦 Current Projects

### user_analytics
**Status**: Production  
**Description**: User behavior analytics processing clickstream data  
**Location**: `user_analytics/`

### event_streaming
**Status**: Production  
**Description**: Real-time event processing with windowed aggregations  
**Location**: `event_streaming/`

### _template
**Status**: Template  
**Description**: Starter template for creating new projects  
**Location**: `_template/`

## 🚀 Quick Commands

```bash
# List all projects
../../../scripts/list-projects.sh

# Create new project
cp -r _template/ my-new-pipeline/
vim my-new-pipeline/PROJECT.yaml

# Test project
cd my-new-pipeline/
pytest tests/

# Deploy project
kubectl apply -k my-new-pipeline/k8s/overlays/prod/
```

## 📚 Documentation

See comprehensive documentation:
- **Project Strategy**: `../../docs/data-platform/project-separation-strategy.md`
- **Quick Reference**: `../../docs/data-platform/PROJECT-QUICK-REF.md`
- **Agent Instructions**: `../../docs/data-platform/agent-guide.md`

## 🔧 Project Standards

Every project must:
- [ ] Have complete `PROJECT.yaml` with all metadata
- [ ] Centralize all config in `config/` directory
- [ ] Include comprehensive documentation in `docs/`
- [ ] Have unit and integration tests
- [ ] Provide test data generators
- [ ] Use common libraries from `../common/`
- [ ] Follow 3-stage pattern (landing, transform, integration)
- [ ] Support multiple environments (dev/staging/prod)
