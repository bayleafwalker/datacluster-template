#!/bin/bash
# Cluster Context Switcher for Datacluster Project

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DATACLUSTER_KUBECONFIG="/projects/dev/datacluster/terraform-v2/kubeconfig"
HOMELAB_KUBECONFIG="$HOME/.kube/config"  # Adjust if different

show_current() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}   Current Kubernetes Context${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    
    if [ -n "$KUBECONFIG" ]; then
        echo -e "KUBECONFIG: ${GREEN}$KUBECONFIG${NC}"
    else
        echo -e "KUBECONFIG: ${YELLOW}(using default ~/.kube/config)${NC}"
    fi
    
    echo ""
    
    if command -v kubectl &> /dev/null; then
        CONTEXT=$(kubectl config current-context 2>/dev/null || echo "none")
        echo -e "Current Context: ${GREEN}$CONTEXT${NC}"
        
        echo ""
        echo "Nodes:"
        kubectl get nodes --no-headers 2>/dev/null | awk '{print "  - " $1 " (" $2 ")"}' || echo "  (unable to connect)"
    else
        echo -e "${RED}kubectl not found${NC}"
    fi
    
    echo ""
}

switch_to_datacluster() {
    if [ ! -f "$DATACLUSTER_KUBECONFIG" ]; then
        echo -e "${RED}Error: Datacluster kubeconfig not found at $DATACLUSTER_KUBECONFIG${NC}"
        exit 1
    fi
    
    export KUBECONFIG="$DATACLUSTER_KUBECONFIG"
    echo -e "${GREEN}✓ Switched to Datacluster (Hetzner Cloud)${NC}"
    echo ""
    echo "Add this to your shell:"
    echo -e "${YELLOW}export KUBECONFIG=$DATACLUSTER_KUBECONFIG${NC}"
    echo ""
    show_current
}

switch_to_homelab() {
    if [ ! -f "$HOMELAB_KUBECONFIG" ]; then
        echo -e "${RED}Error: Homelab kubeconfig not found at $HOMELAB_KUBECONFIG${NC}"
        exit 1
    fi
    
    export KUBECONFIG="$HOMELAB_KUBECONFIG"
    echo -e "${GREEN}✓ Switched to Homelab (Private Cluster)${NC}"
    echo ""
    echo "Add this to your shell:"
    echo -e "${YELLOW}export KUBECONFIG=$HOMELAB_KUBECONFIG${NC}"
    echo ""
    show_current
}

unset_context() {
    unset KUBECONFIG
    echo -e "${GREEN}✓ Unset KUBECONFIG (using default ~/.kube/config)${NC}"
    echo ""
    show_current
}

show_help() {
    cat << EOF
Cluster Context Switcher

Usage: $0 [COMMAND]

Commands:
  datacluster, dc    Switch to Datacluster (Hetzner Cloud)
  homelab, hl        Switch to Homelab (Private Cluster)
  current, status    Show current context and nodes
  unset              Unset KUBECONFIG (use default)
  help               Show this help message

Examples:
  $0 datacluster     # Switch to Hetzner Datacluster
  $0 homelab         # Switch to homelab cluster
  $0 current         # Show current context

Note: This script only sets KUBECONFIG for the current shell.
To persist, add the export command to your shell session.

EOF
}

# Main
case "${1:-current}" in
    datacluster|dc)
        switch_to_datacluster
        ;;
    homelab|hl)
        switch_to_homelab
        ;;
    current|status|show)
        show_current
        ;;
    unset|reset)
        unset_context
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
