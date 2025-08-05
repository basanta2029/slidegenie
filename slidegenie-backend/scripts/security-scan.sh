#!/bin/bash

# SlideGenie Container Security Scanning Script
# =============================================
# Comprehensive security validation for container images and deployments

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCAN_DATE=$(date -u +'%Y-%m-%d_%H-%M-%S')

# Default configuration
IMAGES_TO_SCAN=${IMAGES_TO_SCAN:-"slidegenie/backend:latest,slidegenie/backend:alpine"}
SCAN_OUTPUT_DIR="${PROJECT_ROOT}/security/scan-results"
REPORT_FORMAT=${REPORT_FORMAT:-"json,table,sarif"}
SEVERITY_THRESHOLD=${SEVERITY_THRESHOLD:-"HIGH"}
FAIL_ON_CRITICAL=${FAIL_ON_CRITICAL:-true}
GENERATE_SBOM=${GENERATE_SBOM:-true}
POLICY_CHECK=${POLICY_CHECK:-true}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_section() {
    echo -e "${PURPLE}[SECTION]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
SlideGenie Container Security Scanner

Usage: $0 [OPTIONS]

Options:
    -i, --images IMAGES         Comma-separated list of images to scan
    -o, --output-dir DIR        Output directory for scan results
    -f, --format FORMAT         Report formats (json,table,sarif,cyclonedx,spdx)
    -s, --severity SEVERITY     Minimum severity threshold (LOW,MEDIUM,HIGH,CRITICAL)
    --fail-on-critical         Exit with error code if critical vulnerabilities found
    --no-sbom                  Skip SBOM generation
    --no-policy                Skip policy validation
    --cleanup                  Clean up old scan results
    -h, --help                 Show this help message

Examples:
    $0 --images "slidegenie/backend:latest"
    $0 --severity CRITICAL --fail-on-critical
    $0 --format json,sarif --output-dir ./security-reports
    $0 --cleanup

Environment Variables:
    IMAGES_TO_SCAN             Images to scan (comma-separated)
    SCAN_OUTPUT_DIR            Output directory for results
    REPORT_FORMAT              Report formats
    SEVERITY_THRESHOLD         Minimum severity level
    FAIL_ON_CRITICAL          Fail on critical vulnerabilities (true/false)
    GENERATE_SBOM             Generate SBOM files (true/false)
    POLICY_CHECK              Run policy validation (true/false)
    TRIVY_CONFIG              Path to Trivy configuration file

EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v trivy >/dev/null 2>&1 || missing_tools+=("trivy")
    
    # Check optional tools
    if [[ "$GENERATE_SBOM" == "true" ]] && ! command -v syft >/dev/null 2>&1; then
        log_warning "syft not found. SBOM generation will use Docker."
    fi
    
    if [[ "$POLICY_CHECK" == "true" ]] && ! command -v opa >/dev/null 2>&1; then
        log_warning "opa not found. Policy validation will be skipped."
        POLICY_CHECK=false
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install missing tools:"
        for tool in "${missing_tools[@]}"; do
            case $tool in
                "docker")
                    log_info "  Docker: https://docs.docker.com/get-docker/"
                    ;;
                "trivy")
                    log_info "  Trivy: brew install aquasecurity/trivy/trivy"
                    log_info "         or curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
                    ;;
            esac
        done
        exit 1
    fi
    
    log_success "Prerequisites check completed"
}

# Setup scan environment
setup_scan_environment() {
    log_info "Setting up scan environment..."
    
    # Create output directories
    mkdir -p "$SCAN_OUTPUT_DIR"
    mkdir -p "$SCAN_OUTPUT_DIR/vulnerabilities"
    mkdir -p "$SCAN_OUTPUT_DIR/sbom"
    mkdir -p "$SCAN_OUTPUT_DIR/policies"
    mkdir -p "$SCAN_OUTPUT_DIR/reports"
    
    # Setup Trivy cache
    export TRIVY_CACHE_DIR="${SCAN_OUTPUT_DIR}/.trivy-cache"
    mkdir -p "$TRIVY_CACHE_DIR"
    
    log_success "Scan environment ready"
}

# Update vulnerability database
update_vulnerability_db() {
    log_info "Updating vulnerability database..."
    
    if trivy image --download-db-only; then
        log_success "Vulnerability database updated"
    else
        log_warning "Failed to update vulnerability database, using cached version"
    fi
}

# Scan single image for vulnerabilities
scan_image_vulnerabilities() {
    local image=$1
    local image_safe=$(echo "$image" | tr ':/' '_-')
    
    log_info "Scanning vulnerabilities in: $image"
    
    # Prepare scan arguments
    local scan_args=(
        --format "$REPORT_FORMAT"
        --severity "$SEVERITY_THRESHOLD,CRITICAL"
        --ignore-unfixed
        --security-checks vuln,secret,config
    )
    
    # Add configuration file if it exists
    if [[ -f "$PROJECT_ROOT/security/trivy-scan.yml" ]]; then
        scan_args+=(--config "$PROJECT_ROOT/security/trivy-scan.yml")
    fi
    
    # Scan for vulnerabilities
    for format in $(echo "$REPORT_FORMAT" | tr ',' ' '); do
        local output_file="$SCAN_OUTPUT_DIR/vulnerabilities/${image_safe}_${SCAN_DATE}.${format}"
        
        if trivy image "${scan_args[@]}" --format "$format" --output "$output_file" "$image"; then
            log_success "Vulnerability scan completed: $output_file"
        else
            log_error "Vulnerability scan failed for $image"
            return 1
        fi
    done
    
    # Check for critical vulnerabilities
    if [[ "$FAIL_ON_CRITICAL" == "true" ]]; then
        local critical_count
        critical_count=$(trivy image --format json --severity CRITICAL --quiet "$image" | jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | .VulnerabilityID' | wc -l || echo "0")
        
        if [[ "$critical_count" -gt 0 ]]; then
            log_error "Found $critical_count CRITICAL vulnerabilities in $image"
            return 1
        fi
    fi
    
    return 0
}

# Generate SBOM for image
generate_image_sbom() {
    local image=$1
    local image_safe=$(echo "$image" | tr ':/' '_-')
    
    log_info "Generating SBOM for: $image"
    
    local sbom_file="$SCAN_OUTPUT_DIR/sbom/${image_safe}_${SCAN_DATE}"
    
    # Generate SBOM in multiple formats
    if command -v syft >/dev/null 2>&1; then
        # Use Syft if available
        syft "$image" -o spdx-json="${sbom_file}.spdx.json"
        syft "$image" -o cyclonedx-json="${sbom_file}.cyclonedx.json"
        syft "$image" -o table="${sbom_file}.txt"
        log_success "SBOM generated with Syft: $sbom_file.*"
    else
        # Fallback to Trivy
        trivy image --format cyclonedx --output "${sbom_file}.cyclonedx.json" "$image"
        trivy image --format spdx-json --output "${sbom_file}.spdx.json" "$image"
        log_success "SBOM generated with Trivy: $sbom_file.*"
    fi
}

# Validate image against security policies
validate_image_policies() {
    local image=$1
    local image_safe=$(echo "$image" | tr ':/' '_-')
    
    log_info "Validating security policies for: $image"
    
    if [[ "$POLICY_CHECK" != "true" ]]; then
        log_warning "Policy validation disabled"
        return 0
    fi
    
    # Create policy input data
    local policy_input="$SCAN_OUTPUT_DIR/policies/${image_safe}_input.json"
    
    # Get image information using Docker inspect
    docker image inspect "$image" > "${policy_input}.raw" 2>/dev/null || {
        log_error "Failed to inspect image: $image"
        return 1
    }
    
    # Transform to policy input format
    jq '{
        image: {
            name: .[0].RepoTags[0] | split(":")[0],
            tag: .[0].RepoTags[0] | split(":")[1],
            id: .[0].Id
        },
        container: {
            user: (.[0].Config.User // "root"),
            exposed_ports: ([.[0].Config.ExposedPorts // {} | keys[] | split("/")[0] | tonumber]),
            environment: [.[0].Config.Env[] | split("=") | {name: .[0], value: .[1]}],
            volumes: ([.[0].Config.Volumes // {} | keys]),
            working_dir: .[0].Config.WorkingDir,
            cmd: .[0].Config.Cmd,
            entrypoint: .[0].Config.Entrypoint
        },
        environment: "production"
    }' "${policy_input}.raw" > "$policy_input"
    
    # Run policy evaluation
    if command -v opa >/dev/null 2>&1; then
        local policy_file="$PROJECT_ROOT/security/security-policies.rego"
        local policy_output="$SCAN_OUTPUT_DIR/policies/${image_safe}_${SCAN_DATE}.json"
        
        if [[ -f "$policy_file" ]]; then
            opa eval -d "$policy_file" -i "$policy_input" "data.slidegenie.security.allow" > "$policy_output"
            
            # Check policy result
            local policy_result
            policy_result=$(jq -r '.result[0].expressions[0].value' "$policy_output")
            
            if [[ "$policy_result" == "true" ]]; then
                log_success "Security policy validation passed for $image"
            else
                log_error "Security policy validation failed for $image"
                
                # Get violations
                opa eval -d "$policy_file" -i "$policy_input" "data.slidegenie.security.violations" | \
                jq -r '.result[0].expressions[0].value[]?' | while read -r violation; do
                    log_error "  Policy violation: $violation"
                done
                
                return 1
            fi
        else
            log_warning "Security policy file not found: $policy_file"
        fi
    else
        log_warning "OPA not available, skipping policy validation"
    fi
}

# Scan Docker configuration
scan_docker_config() {
    log_info "Scanning Docker configuration..."
    
    local config_output="$SCAN_OUTPUT_DIR/docker_config_${SCAN_DATE}.json"
    
    # Scan Dockerfile if exists
    if [[ -f "$PROJECT_ROOT/Dockerfile" ]]; then
        trivy config --format json --output "$config_output" "$PROJECT_ROOT"
        log_success "Docker configuration scan completed: $config_output"
    else
        log_warning "No Dockerfile found for configuration scanning"
    fi
}

# Generate comprehensive security report
generate_security_report() {
    log_info "Generating comprehensive security report..."
    
    local report_file="$SCAN_OUTPUT_DIR/reports/security_report_${SCAN_DATE}.md"
    
    cat > "$report_file" << EOF
# SlideGenie Security Scan Report

**Generated:** $(date -u +'%Y-%m-%d %H:%M:%S UTC')  
**Scan ID:** $SCAN_DATE  
**Images Scanned:** $(echo "$IMAGES_TO_SCAN" | tr ',' ' ')

## Executive Summary

EOF
    
    # Add vulnerability summary
    for image in $(echo "$IMAGES_TO_SCAN" | tr ',' ' '); do
        local image_safe=$(echo "$image" | tr ':/' '_-')
        local vuln_file="$SCAN_OUTPUT_DIR/vulnerabilities/${image_safe}_${SCAN_DATE}.json"
        
        if [[ -f "$vuln_file" ]]; then
            cat >> "$report_file" << EOF
### $image

EOF
            
            # Count vulnerabilities by severity
            local critical high medium low
            critical=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | .VulnerabilityID' "$vuln_file" 2>/dev/null | wc -l || echo "0")
            high=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH") | .VulnerabilityID' "$vuln_file" 2>/dev/null | wc -l || echo "0")
            medium=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM") | .VulnerabilityID' "$vuln_file" 2>/dev/null | wc -l || echo "0")
            low=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW") | .VulnerabilityID' "$vuln_file" 2>/dev/null | wc -l || echo "0")
            
            cat >> "$report_file" << EOF
| Severity | Count |
|----------|-------|
| CRITICAL | $critical |
| HIGH     | $high |
| MEDIUM   | $medium |
| LOW      | $low |

EOF
        fi
    done
    
    cat >> "$report_file" << EOF

## Detailed Findings

For detailed vulnerability information, see individual scan files in:
- Vulnerabilities: \`$SCAN_OUTPUT_DIR/vulnerabilities/\`
- SBOM Files: \`$SCAN_OUTPUT_DIR/sbom/\`
- Policy Results: \`$SCAN_OUTPUT_DIR/policies/\`

## Recommendations

1. **Critical Vulnerabilities**: Address all critical vulnerabilities immediately
2. **High Vulnerabilities**: Plan remediation within 48 hours
3. **Medium Vulnerabilities**: Address during next maintenance window
4. **Policy Violations**: Review and remediate security policy failures
5. **Dependencies**: Keep base images and dependencies updated

## Next Steps

1. Review detailed scan results
2. Create remediation plan
3. Update base images and dependencies
4. Re-scan after fixes
5. Update security policies as needed

---
Generated by SlideGenie Security Scanner
EOF
    
    log_success "Security report generated: $report_file"
}

# Cleanup old scan results
cleanup_old_results() {
    log_info "Cleaning up old scan results..."
    
    # Keep last 30 days of results
    find "$SCAN_OUTPUT_DIR" -name "*_202*" -type f -mtime +30 -delete 2>/dev/null || true
    
    # Clean up empty directories
    find "$SCAN_OUTPUT_DIR" -type d -empty -delete 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Send notification
send_notification() {
    local status=$1
    local message=$2
    
    # Slack notification if webhook is configured
    if [[ -n "${SLACK_WEBHOOK:-}" ]]; then
        local color="good"
        [[ "$status" == "error" ]] && color="danger"
        [[ "$status" == "warning" ]] && color="warning"
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"color\":\"$color\",\"text\":\"SlideGenie Security Scan: $message\"}" \
            "$SLACK_WEBHOOK" >/dev/null 2>&1 || true
    fi
    
    # Email notification if configured
    if [[ -n "${EMAIL_RECIPIENT:-}" && -n "${SMTP_HOST:-}" ]]; then
        echo "$message" | mail -s "SlideGenie Security Scan Report" "$EMAIL_RECIPIENT" 2>/dev/null || true
    fi
}

# Main execution
main() {
    local cleanup_only=false
    local scan_failed=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--images)
                IMAGES_TO_SCAN="$2"
                shift 2
                ;;
            -o|--output-dir)
                SCAN_OUTPUT_DIR="$2"
                shift 2
                ;;
            -f|--format)
                REPORT_FORMAT="$2"
                shift 2
                ;;
            -s|--severity)
                SEVERITY_THRESHOLD="$2"
                shift 2
                ;;
            --fail-on-critical)
                FAIL_ON_CRITICAL=true
                shift
                ;;
            --no-sbom)
                GENERATE_SBOM=false
                shift
                ;;
            --no-policy)
                POLICY_CHECK=false
                shift
                ;;
            --cleanup)
                cleanup_only=true
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
    
    log_section "SlideGenie Container Security Scanner"
    log_info "Scan ID: $SCAN_DATE"
    log_info "Images: $IMAGES_TO_SCAN"
    log_info "Output: $SCAN_OUTPUT_DIR"
    log_info "Formats: $REPORT_FORMAT"
    log_info "Severity: $SEVERITY_THRESHOLD+"
    
    # Setup environment
    check_prerequisites
    setup_scan_environment
    
    # Cleanup only mode
    if [[ "$cleanup_only" == "true" ]]; then
        cleanup_old_results
        exit 0
    fi
    
    # Update vulnerability database
    update_vulnerability_db
    
    # Scan each image
    for image in $(echo "$IMAGES_TO_SCAN" | tr ',' ' '); do
        log_section "Scanning: $image"
        
        # Check if image exists
        if ! docker image inspect "$image" >/dev/null 2>&1; then
            log_error "Image not found: $image"
            scan_failed=true
            continue
        fi
        
        # Vulnerability scanning
        if ! scan_image_vulnerabilities "$image"; then
            scan_failed=true
        fi
        
        # SBOM generation
        if [[ "$GENERATE_SBOM" == "true" ]]; then
            generate_image_sbom "$image"
        fi
        
        # Policy validation
        if ! validate_image_policies "$image"; then
            scan_failed=true
        fi
    done
    
    # Scan Docker configuration
    scan_docker_config
    
    # Generate comprehensive report
    generate_security_report
    
    # Cleanup old results
    cleanup_old_results
    
    # Final status
    if [[ "$scan_failed" == "true" ]]; then
        log_error "Security scan completed with failures"
        send_notification "error" "Security scan failed - critical vulnerabilities or policy violations found"
        exit 1
    else
        log_success "Security scan completed successfully"
        send_notification "good" "Security scan passed - no critical issues found"
        
        # Display summary
        log_section "Scan Summary"
        log_info "Results saved to: $SCAN_OUTPUT_DIR"
        log_info "Report available at: $SCAN_OUTPUT_DIR/reports/security_report_${SCAN_DATE}.md"
        
        exit 0
    fi
}

# Trap for cleanup on exit
trap cleanup_old_results EXIT

# Run main function
main "$@"