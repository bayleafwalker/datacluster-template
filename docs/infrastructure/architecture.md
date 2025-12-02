# Architecture

## Infrastructure

**2-node Kubernetes cluster on Talos OS** (Hetzner Cloud):
- **Talos OS**: v1.11.5 (immutable Linux, API-managed, no SSH)
- **Kubernetes**: v1.34.1
- **CNI**: Cilium v1.18.3 (eBPF-based networking, pod-to-pod encryption capable)
- **Control-plane**: CX23 (2 vCPU, 4GB RAM, workloads enabled for cost optimization)
- **Worker**: CX33 (4 vCPU, 8GB RAM)
- **Network**: 10.0.0.0/16 private (10.0.1.0/24 nodes, 10.0.16.0/20 pods, 10.0.8.0/21 services)
- **Access**: Tailscale VPN system extension (built into Talos image via Packer)
- **Cost**: €11.27/month (€10.01 servers + €1.26 public IPv4 addresses)

## Component breakdown

| Layer | Component | Purpose |
|-------|-----------|---------|
|Compute|**Talos Kubernetes** on Hetzner Cloud|Immutable OS, container orchestration, network & volume management|
|Data Engine|**Spark Operator**|Turns Spark jobs into first-class K8s resources (`SparkApplication`)|
|Storage|**Hetzner Volumes** (CSI driver)|Block storage for checkpoints, streaming state, local data (50-100GB PVCs)|
| |**Hetzner Object Storage**|S3-compatible object store for large datasets, parquet files, history logs|
|Observability|**Prometheus**|Scrapes cluster + Spark JVM metrics (via JMX Exporter)|
| |**Grafana**|Dashboards (K8s / Spark / Streaming throughput) + Alerting rules|
|Automation|**FluxCD GitOps**|Declarative cluster state from Git |
|IaC|**Terraform**|Provisions Hetzner servers, networks, volumes, firewalls|
|Security|**Tailscale VPN**|Secure WireGuard-based VPN, integrated as Talos system extension|
| |**SOPS + age**|Encrypts secrets (IPs, tokens, keys) in Git|
| |**Hetzner Firewall**|Restricts access to Kubernetes API (6443), Talos API (50000), Cilium health checks|

---

## Data flow

1. **Source data** lands in Hetzner Object Storage (S3-compatible) or uploaded to Hetzner Volumes.  
2. A **SparkApplication** (batch) reads, transforms with PySpark/SQL, and writes results to Object Storage.  
3. A **streaming job** consumes events (rate source, Kafka, etc.) and appends outputs, checkpointing to Hetzner Volumes.  
4. **Spark dynamic allocation** scales executors based on workload; scales to zero when idle.  
5. Metrics from Spark pods are scraped by Prometheus; dashboards update live in Grafana.  

---

## Scaling

- Add worker nodes via Terraform `worker_nodes` config
- Update Talos config for new nodes
- Spark dynamic allocation scales executors based on workload
- Control-plane runs workloads (cost optimization)  
