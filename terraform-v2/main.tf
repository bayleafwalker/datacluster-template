terraform {
  required_version = ">= 1.0"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.57"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

# The hcloud-talos module automatically discovers the custom Talos images
# we built with Packer (they have os=talos label)
#
# COST NOTE: Public IPv4 addresses cost €0.63/month each (€1.26/mo total for 2 servers)
# This cost is UNAVOIDABLE because:
# - Hetzner Cloud Networks don't provide NAT gateway
# - Without public IPs, servers have no internet connectivity
# - Tailscale requires internet access to coordination servers
# - Container registries require internet access
# IPv6-only is not yet supported by this Talos module

module "talos" {
  source  = "hcloud-talos/talos/hcloud"
  version = "2.20.7"

  # Required variables
  hcloud_token    = var.hcloud_token
  cluster_name    = "datacluster"
  datacenter_name = "hel1-dc2"  # Helsinki datacenter
  
  # Talos and Kubernetes versions (latest stable as of Dec 2025)
  talos_version      = "v1.11.5"
  kubernetes_version = "v1.34.1"
  
  # Control plane configuration (1 node with workloads enabled)
  control_plane_count       = 1
  control_plane_server_type = "cx23"  # 2 vCPU, 4GB RAM (€3.75/mo - cheaper than cx22)
  
  # Worker node configuration (1 worker)
  worker_nodes = [
    {
      type   = "cx33"  # 4 vCPU, 8GB RAM (€6.26/mo - cheaper than cx32)
      count  = 1
      labels = {
        "node.kubernetes.io/role" = "worker"
      }
      taints = []
    }
  ]
  
  # Allow scheduling on control plane (cost optimization)
  control_plane_allow_schedule = true
  
  # Network configuration
  network_ipv4_cidr = "10.0.0.0/16"
  node_ipv4_cidr    = "10.0.1.0/24"
  pod_ipv4_cidr     = "10.0.16.0/20"
  service_ipv4_cidr = "10.0.8.0/21"
  
  # Disable IPv6 (not needed, cost optimization)
  enable_ipv6 = false
  
  # Firewall configuration (allow all, access secured via Tailscale)
  firewall_use_current_ip  = false
  firewall_kube_api_source = ["0.0.0.0/0", "::/0"]
  firewall_talos_api_source = ["0.0.0.0/0", "::/0"]
  
  # Tailscale configuration
  tailscale = {
    enabled  = true
    auth_key = var.tailscale_auth_key
  }
  
  # Cilium CNI configuration (latest stable)
  cilium_version = "v1.18.3"
}
