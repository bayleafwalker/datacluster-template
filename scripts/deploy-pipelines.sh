#!/bin/bash
# Pipeline Build and Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
IMAGE_NAME="${IMAGE_NAME:-ghcr.io/bayleafwalker/datacluster-spark}"
IMAGE_TAG="${IMAGE_TAG:-0.1.0}"
NAMESPACE="${NAMESPACE:-spark-operator}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    commands=("docker" "kubectl")
    for cmd in "${commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd is not installed. Please install it first."
            exit 1
        fi
    done
    
    # Check kubectl connectivity
    if ! kubectl get nodes &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
        exit 1
    fi
    
    log_info "✓ All prerequisites met"
}

build_image() {
    log_info "Building Spark application image..."
    
    cd "$PROJECT_ROOT/src"
    
    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" -f Dockerfile .
    
    if [ $? -eq 0 ]; then
        log_info "✓ Image built: ${IMAGE_NAME}:${IMAGE_TAG}"
    else
        log_error "Image build failed"
        exit 1
    fi
}

push_image() {
    log_info "Pushing image to registry..."
    
    # Check if logged in to GHCR
    if ! docker info | grep -q "Username"; then
        log_warn "You may need to login to GitHub Container Registry:"
        log_warn "  echo \$GITHUB_TOKEN | docker login ghcr.io -u bayleafwalker --password-stdin"
    fi
    
    docker push "${IMAGE_NAME}:${IMAGE_TAG}"
    
    if [ $? -eq 0 ]; then
        log_info "✓ Image pushed: ${IMAGE_NAME}:${IMAGE_TAG}"
    else
        log_error "Image push failed"
        exit 1
    fi
}

deploy_pipelines() {
    log_info "Deploying SparkApplications..."
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warn "Namespace $NAMESPACE does not exist. Creating it..."
        kubectl create namespace "$NAMESPACE"
    fi
    
    # Apply pipelines
    kubectl apply -f "$PROJECT_ROOT/pipelines/sample-pipelines.yaml"
    
    if [ $? -eq 0 ]; then
        log_info "✓ Pipelines deployed"
    else
        log_error "Pipeline deployment failed"
        exit 1
    fi
}

show_status() {
    log_info "Checking deployment status..."
    echo ""
    
    echo "=== SparkApplications ==="
    kubectl get sparkapplications -n "$NAMESPACE"
    echo ""
    
    echo "=== Pods ==="
    kubectl get pods -n "$NAMESPACE"
    echo ""
    
    log_info "Monitor logs with:"
    echo "  kubectl logs -n $NAMESPACE -l spark-role=driver -f"
    echo ""
    
    log_info "Access Spark UI:"
    echo "  kubectl port-forward -n $NAMESPACE <driver-pod-name> 4040:4040"
    echo ""
    
    log_info "Access Grafana dashboard:"
    echo "  kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80"
    echo "  Open: http://localhost:3000 (admin/admin)"
}

# Main execution
main() {
    log_info "=== Datacluster Pipeline Deployment ==="
    log_info "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    log_info "Namespace: ${NAMESPACE}"
    echo ""
    
    case "${1:-all}" in
        build)
            check_prerequisites
            build_image
            ;;
        push)
            check_prerequisites
            push_image
            ;;
        deploy)
            check_prerequisites
            deploy_pipelines
            show_status
            ;;
        all)
            check_prerequisites
            build_image
            push_image
            deploy_pipelines
            show_status
            ;;
        status)
            show_status
            ;;
        *)
            echo "Usage: $0 {build|push|deploy|all|status}"
            echo ""
            echo "Commands:"
            echo "  build   - Build Docker image only"
            echo "  push    - Push image to registry only"
            echo "  deploy  - Deploy SparkApplications only"
            echo "  all     - Build, push, and deploy (default)"
            echo "  status  - Show current deployment status"
            echo ""
            echo "Environment Variables:"
            echo "  IMAGE_NAME  - Docker image name (default: ghcr.io/bayleafwalker/datacluster-spark)"
            echo "  IMAGE_TAG   - Image tag (default: 0.1.0)"
            echo "  NAMESPACE   - Kubernetes namespace (default: spark-operator)"
            exit 1
            ;;
    esac
    
    log_info "=== Done ==="
}

main "$@"
