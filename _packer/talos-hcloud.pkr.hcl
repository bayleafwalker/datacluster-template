# hcloud.pkr.hcl - x86_64 only (ARM removed)
packer {
  required_plugins {
    hcloud = {
      version = "v1.7.0"
      source  = "github.com/hetznercloud/hcloud"
    }
  }
}

variable "talos_version" {
  type    = string
  default = "v1.11.5"
}

variable "image_url_x86" {
  type    = string
  default = null
}

variable "server_location" {
  type    = string
  default = "hel1"
}

locals {
  # Default image with Tailscale extension (schematic ID: 4a0d65c669d46663f377e7161e50cfd570c401f26fd9e7bda34a0216b6f1922b)
  image_x86 = var.image_url_x86 != null ? var.image_url_x86 : "https://factory.talos.dev/image/4a0d65c669d46663f377e7161e50cfd570c401f26fd9e7bda34a0216b6f1922b/${var.talos_version}/hcloud-amd64.raw.xz"

  # Inline shell commands
  download_image = "wget --timeout=5 --waitretry=5 --tries=5 --retry-connrefused --inet4-only -O /tmp/talos.raw.xz "

  write_image = <<-EOT
    set -ex
    echo 'Talos image loaded, writing to disk... '
    xz -d -c /tmp/talos.raw.xz | dd of=/dev/sda && sync
    echo 'done.'
  EOT

  clean_up = <<-EOT
    set -ex
    echo "Cleaning-up..."
    rm -rf /etc/ssh/ssh_host_*
  EOT
}

# Source for the Talos x86_64 image
source "hcloud" "talos-x86" {
  rescue       = "linux64"
  image        = "debian-11"
  location     = "${var.server_location}"
  server_type  = "cx22"
  ssh_username = "root"

  snapshot_name   = "Talos Linux ${var.talos_version} x86 with Tailscale"
  snapshot_labels = {
    type       = "infra",
    os         = "talos",
    version    = "${var.talos_version}",
    arch       = "x86",
    creator    = "datacluster",
    extensions = "tailscale"
  }
}

# Build the Talos x86_64 snapshot
build {
  sources = ["source.hcloud.talos-x86"]

  # Download the Talos x86 image
  provisioner "shell" {
    inline = ["${local.download_image}${local.image_x86}"]
  }

  # Write the Talos x86 image to the disk
  provisioner "shell" {
    inline = [local.write_image]
  }

  # Clean-up
  provisioner "shell" {
    inline = [local.clean_up]
  }
}
