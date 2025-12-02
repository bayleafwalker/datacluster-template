# Talos version for image building
talos_version = "v1.11.5"

# Custom image URL with Tailscale extension (x86_64 only)
# Generated from: curl -X POST --data-binary @schematic.yaml https://factory.talos.dev/schematics
# Schematic ID: 4a0d65c669d46663f377e7161e50cfd570c401f26fd9e7bda34a0216b6f1922b
image_url_x86 = "https://factory.talos.dev/image/4a0d65c669d46663f377e7161e50cfd570c401f26fd9e7bda34a0216b6f1922b/v1.11.5/hcloud-amd64.raw.xz"

# Hetzner datacenter location
server_location = "hel1"
