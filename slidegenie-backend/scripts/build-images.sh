#!/bin/bash

# SlideGenie Docker Image Build Automation Script
# ==============================================
# Builds optimized Docker images with security scanning and multi-architecture support

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION=${VERSION:-$(git describe --tags --always 2>/dev/null || echo "dev")}

# Docker configuration
REGISTRY=${REGISTRY:-"slidegenie"}
IMAGE_NAME=${IMAGE_NAME:-"backend"}
PLATFORMS=${PLATFORMS:-"linux/amd64,linux/arm64"}
PUSH=${PUSH:-false}
CACHE=${CACHE:-true}
SCAN=${SCAN:-true}
SIGN=${SIGN:-false}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
SlideGenie Docker Image Build Script

Usage: $0 [OPTIONS]

Options:
    -r, --registry REGISTRY     Docker registry (default: slidegenie)
    -n, --name NAME            Image name (default: backend)
    -v, --version VERSION      Image version (default: git describe)
    -p, --platforms PLATFORMS  Target platforms (default: linux/amd64,linux/arm64)
    --push                     Push images to registry
    --no-cache                 Disable build cache
    --no-scan                  Skip security scanning
    --sign                     Sign images with cosign
    --alpine                   Build Alpine variant
    --minimal                  Build minimal Alpine variant
    --all                      Build all variants
    -h, --help                 Show this help message

Examples:
    $0 --push --version 1.0.0
    $0 --alpine --scan
    $0 --all --push --sign
    
Environment Variables:
    REGISTRY                   Docker registry
    IMAGE_NAME                 Image name
    VERSION                    Image version
    PLATFORMS                  Target platforms
    PUSH                       Push to registry (true/false)
    CACHE                      Enable build cache (true/false)
    SCAN                       Enable security scanning (true/false)
    SIGN                       Sign images (true/false)
    DOCKER_BUILDKIT            Enable BuildKit (default: 1)
    BUILDX_NO_DEFAULT_ATTESTATIONS  Disable attestations (default: 1)

EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Buildx
    if ! docker buildx version &> /dev/null; then
        log_error "Docker Buildx is not available"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check Trivy for security scanning
    if [[ "$SCAN" == "true" ]] && ! command -v trivy &> /dev/null; then
        log_warning "Trivy not found. Installing via Docker..."
    fi
    
    # Check cosign for image signing
    if [[ "$SIGN" == "true" ]] && ! command -v cosign &> /dev/null; then
        log_warning "Cosign not found. Image signing will be skipped."
        SIGN=false
    fi
    
    log_success "Prerequisites check completed"
}

# Setup Docker Buildx
setup_buildx() {
    log_info "Setting up Docker Buildx..."
    
    # Create builder instance if it doesn't exist
    if ! docker buildx inspect slidegenie-builder &> /dev/null; then
        log_info "Creating new Buildx builder instance..."
        docker buildx create \
            --name slidegenie-builder \
            --driver docker-container \
            --bootstrap \
            --use
    else
        docker buildx use slidegenie-builder
    fi
    
    # Verify builder supports required platforms
    log_info "Verifying platform support..."
    docker buildx inspect --bootstrap
    
    log_success "Buildx setup completed"
}

# Build image function
build_image() {
    local dockerfile=$1
    local target=$2
    local tag_suffix=$3
    local extra_args=${4:-""}
    
    local full_tag="${REGISTRY}/${IMAGE_NAME}:${VERSION}${tag_suffix}"
    local latest_tag="${REGISTRY}/${IMAGE_NAME}:latest${tag_suffix}"
    
    log_info "Building image: $full_tag"
    log_info "Dockerfile: $dockerfile"
    log_info "Target: $target"
    
    # Prepare build arguments
    local build_args=(
        --file "$dockerfile"
        --target "$target"
        --platform "$PLATFORMS"
        --build-arg "BUILD_DATE=$BUILD_DATE"
        --build-arg "VCS_REF=$VCS_REF"
        --tag "$full_tag"
        --tag "$latest_tag"
    )
    
    # Add cache options
    if [[ "$CACHE" == "true" ]]; then
        build_args+=(
            --cache-from "type=gha"
            --cache-to "type=gha,mode=max"
        )
    else
        build_args+=(--no-cache)
    fi
    
    # Add push option
    if [[ "$PUSH" == "true" ]]; then
        build_args+=(--push)
    else
        build_args+=(--load)
    fi
    
    # Add extra arguments
    if [[ -n "$extra_args" ]]; then
        read -ra extra_array <<< "$extra_args"
        build_args+=("${extra_array[@]}")
    fi
    
    # Build the image
    if docker buildx build "${build_args[@]}" "$PROJECT_ROOT"; then
        log_success "Successfully built: $full_tag"
        
        # Security scan if enabled and not pushing multi-platform
        if [[ "$SCAN" == "true" && "$PLATFORMS" == "linux/amd64" ]]; then
            scan_image "$full_tag"
        fi
        
        # Sign image if enabled
        if [[ "$SIGN" == "true" && "$PUSH" == "true" ]]; then
            sign_image "$full_tag"
        fi
        
        return 0
    else
        log_error "Failed to build: $full_tag"
        return 1
    fi
}

# Security scanning function
scan_image() {
    local image=$1
    
    log_info "Scanning image for vulnerabilities: $image"
    
    # Create scan results directory
    mkdir -p "$PROJECT_ROOT/security/scan-results"
    
    local scan_output="$PROJECT_ROOT/security/scan-results/trivy-$(basename "$image" | tr ':' '-')-$(date +%Y%m%d-%H%M%S).json"
    
    # Run Trivy scan
    if command -v trivy &> /dev/null; then
        trivy image \
            --format json \
            --output "$scan_output" \
            --severity HIGH,CRITICAL \
            --ignore-unfixed \
            "$image"
    else
        # Use Docker to run Trivy
        docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$PROJECT_ROOT/security/scan-results":/output \
            aquasec/trivy:latest image \
            --format json \
            --output "/output/$(basename "$scan_output")" \
            --severity HIGH,CRITICAL \
            --ignore-unfixed \
            "$image"
    fi
    
    # Check scan results
    local critical_count=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | .VulnerabilityID' "$scan_output" 2>/dev/null | wc -l || echo "0")
    local high_count=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH") | .VulnerabilityID' "$scan_output" 2>/dev/null | wc -l || echo "0")
    
    if [[ "$critical_count" -gt 0 ]]; then
        log_error "Found $critical_count CRITICAL vulnerabilities in $image"
        log_warning "Scan results saved to: $scan_output"
        return 1
    elif [[ "$high_count" -gt 0 ]]; then
        log_warning "Found $high_count HIGH vulnerabilities in $image"
        log_info "Scan results saved to: $scan_output"
    else
        log_success "No HIGH or CRITICAL vulnerabilities found in $image"
    fi
    
    return 0
}

# Image signing function
sign_image() {
    local image=$1
    
    log_info "Signing image: $image"
    
    if cosign sign --yes "$image"; then
        log_success "Successfully signed: $image"
    else
        log_error "Failed to sign: $image"
        return 1
    fi
}

# Generate SBOM (Software Bill of Materials)
generate_sbom() {
    local image=$1
    
    log_info "Generating SBOM for: $image"
    
    mkdir -p "$PROJECT_ROOT/security/sbom"
    local sbom_file="$PROJECT_ROOT/security/sbom/sbom-$(basename "$image" | tr ':' '-')-$(date +%Y%m%d-%H%M%S).json"
    
    # Use Syft to generate SBOM
    if command -v syft &> /dev/null; then
        syft "$image" -o spdx-json > "$sbom_file"
        log_success "SBOM generated: $sbom_file"
    else
        # Use Docker to run Syft
        docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$PROJECT_ROOT/security/sbom":/output \
            anchore/syft:latest \
            "$image" -o spdx-json > "$sbom_file"
        log_success "SBOM generated: $sbom_file"
    fi
}

# Build standard Debian-based images
build_standard_images() {
    log_info "Building standard Debian-based images..."
    
    # Development image
    build_image "Dockerfile" "development" "-dev" || return 1
    
    # Production image
    build_image "Dockerfile" "production" "" || return 1
    
    # Testing image
    build_image "Dockerfile" "testing" "-test" || return 1
    
    log_success "Standard images built successfully"
}

# Build Alpine-based images
build_alpine_images() {
    log_info "Building Alpine-based images..."
    
    # Alpine development
    build_image "Dockerfile.alpine" "alpine-development" "-alpine-dev" || return 1
    
    # Alpine production
    build_image "Dockerfile.alpine" "alpine-production" "-alpine" || return 1
    
    # Alpine testing
    build_image "Dockerfile.alpine" "alpine-testing" "-alpine-test" || return 1
    
    log_success "Alpine images built successfully"
}

# Build minimal Alpine images
build_minimal_images() {
    log_info "Building minimal Alpine images..."
    
    # Minimal Alpine production
    build_image "Dockerfile.alpine" "alpine-minimal" "-minimal" || return 1
    
    log_success "Minimal images built successfully"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    
    # Remove dangling images
    docker image prune -f &> /dev/null || true
    
    # Remove builder cache if not caching
    if [[ "$CACHE" != "true" ]]; then
        docker buildx prune -f &> /dev/null || true
    fi
    
    log_success "Cleanup completed"
}

# Main execution
main() {
    local build_alpine=false
    local build_minimal=false
    local build_all=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -n|--name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -p|--platforms)
                PLATFORMS="$2"
                shift 2
                ;;
            --push)
                PUSH=true
                shift
                ;;
            --no-cache)
                CACHE=false
                shift
                ;;
            --no-scan)
                SCAN=false
                shift
                ;;
            --sign)
                SIGN=true
                shift
                ;;
            --alpine)
                build_alpine=true
                shift
                ;;
            --minimal)
                build_minimal=true
                shift
                ;;
            --all)
                build_all=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Set Docker Buildx environment
    export DOCKER_BUILDKIT=1
    export BUILDX_NO_DEFAULT_ATTESTATIONS=1
    
    log_info "Starting SlideGenie Docker image build"
    log_info "Registry: $REGISTRY"
    log_info "Image: $IMAGE_NAME"
    log_info "Version: $VERSION"
    log_info "Platforms: $PLATFORMS"
    log_info "Push: $PUSH"
    log_info "Cache: $CACHE"
    log_info "Scan: $SCAN"
    log_info "Sign: $SIGN"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Run checks and setup
    check_prerequisites
    setup_buildx
    
    # Build images based on options
    local build_failed=false
    
    if [[ "$build_all" == "true" ]]; then
        build_standard_images || build_failed=true
        build_alpine_images || build_failed=true
        build_minimal_images || build_failed=true
    else
        # Build standard images by default
        build_standard_images || build_failed=true
        
        if [[ "$build_alpine" == "true" ]]; then
            build_alpine_images || build_failed=true
        fi
        
        if [[ "$build_minimal" == "true" ]]; then
            build_minimal_images || build_failed=true
        fi
    fi
    
    # Cleanup
    cleanup
    
    # Final status
    if [[ "$build_failed" == "true" ]]; then
        log_error "Some builds failed. Check the output above for details."
        exit 1
    else
        log_success "All builds completed successfully!"
        
        if [[ "$PUSH" == "true" ]]; then
            log_success "Images pushed to registry: $REGISTRY"
        else
            log_info "Images built locally. Use --push to push to registry."
        fi
    fi
}

# Trap for cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"