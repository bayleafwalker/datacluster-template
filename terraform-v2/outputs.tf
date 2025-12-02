output "control_plane_public_ips" {
  description = "Public IPv4 addresses of control plane nodes"
  value       = module.talos.public_ipv4_list
}

output "talosconfig" {
  description = "Talos configuration for talosctl"
  value       = module.talos.talosconfig
  sensitive   = true
}

output "kubeconfig" {
  description = "Kubernetes configuration"
  value       = module.talos.kubeconfig
  sensitive   = true
}

output "kubeconfig_data" {
  description = "Structured kubeconfig data"
  value       = module.talos.kubeconfig_data
  sensitive   = true
}

output "network_id" {
  description = "Hetzner Cloud Network ID"
  value       = module.talos.hetzner_network_id
}
