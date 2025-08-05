# SlideGenie Container Optimization Guide

## Overview

This document provides comprehensive guidance for the optimized containerization setup of SlideGenie, featuring multi-stage builds, Alpine variants, security scanning, and size optimization.

## 🏗️ Container Architecture

### Multi-Stage Build Strategy

Our containerization approach uses multiple stages to optimize for different use cases:

1. **Builder Stage**: Full development environment with build tools
2. **Production Stage**: Minimal runtime environment 
3. **Development Stage**: Development-friendly with hot reload
4. **Testing Stage**: Includes testing tools and utilities
5. **Alpine Variants**: Ultra-lightweight Alpine Linux alternatives

## 📁 File Structure

```
├── Dockerfile                  # Multi-stage Debian-based build
├── Dockerfile.alpine           # Alpine-based variants
├── .dockerignore              # Build context optimization
├── docker-compose.prod.yml    # Production deployment
├── .env.production            # Production environment template
├── scripts/
│   └── build-images.sh        # Automated build script
├── security/
│   ├── trivy-scan.yml         # Security scanning configuration
│   └── container-security.yml # Security policies
└── monitoring/
    └── prometheus.yml         # Monitoring configuration
```

## 🔨 Build Variants

### Standard Debian Images

Built from `python:3.11-slim` with comprehensive system dependencies:

- **Production**: `slidegenie/backend:latest`
- **Development**: `slidegenie/backend:dev`
- **Testing**: `slidegenie/backend:test`

### Alpine Images

Ultra-lightweight variants from `python:3.11-alpine3.18`:

- **Alpine Production**: `slidegenie/backend:alpine`
- **Alpine Development**: `slidegenie/backend:alpine-dev`
- **Alpine Testing**: `slidegenie/backend:alpine-test`
- **Minimal**: `slidegenie/backend:minimal`

## 🚀 Quick Start

### Building Images

```bash
# Build all variants
./scripts/build-images.sh --all

# Build only Alpine variants
./scripts/build-images.sh --alpine

# Build with security scanning
./scripts/build-images.sh --scan

# Build and push to registry
./scripts/build-images.sh --push --version 1.0.0
```

### Running Containers

```bash
# Development environment
docker-compose up -d

# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Single container testing
docker run -p 8000:8000 slidegenie/backend:latest
```

## 🔧 Build Script Usage

The `scripts/build-images.sh` script provides comprehensive build automation:

### Basic Usage

```bash
./scripts/build-images.sh [OPTIONS]

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
  -h, --help                 Show help message
```

### Examples

```bash
# Build and scan production image
./scripts/build-images.sh --scan --version 1.2.0

# Build all variants for multiple architectures
./scripts/build-images.sh --all --platforms linux/amd64,linux/arm64

# Build, scan, sign, and push to registry
./scripts/build-images.sh --all --scan --sign --push --version 1.0.0
```

## 🔒 Security Features

### Container Security Hardening

- **Non-root user**: All containers run as user `slidegenie` (UID 1000)
- **Read-only filesystem**: Where possible, with specific writable volumes
- **Security options**: `no-new-privileges:true`, proper capabilities
- **Minimal attack surface**: Only essential packages and dependencies

### Vulnerability Scanning

Automated security scanning with Trivy:

```bash
# Manual security scan
trivy image slidegenie/backend:latest

# Scan with custom configuration
trivy --config security/trivy-scan.yml image slidegenie/backend:latest

# Generate SBOM
syft slidegenie/backend:latest -o spdx-json > sbom.json
```

### Image Signing

Images can be signed with Cosign for supply chain security:

```bash
# Sign image
cosign sign --yes slidegenie/backend:latest

# Verify signature
cosign verify slidegenie/backend:latest
```

## 📊 Size Optimization

### Image Size Comparison

| Variant | Base Image | Compressed Size | Uncompressed Size |
|---------|------------|-----------------|-------------------|
| Standard Production | python:3.11-slim | ~300MB | ~800MB |
| Alpine Production | python:3.11-alpine | ~150MB | ~400MB |
| Alpine Minimal | python:3.11-alpine | ~100MB | ~300MB |

### Optimization Techniques

1. **Multi-stage builds**: Separate build and runtime environments
2. **Layer optimization**: Minimize layers and cache-bust appropriately
3. **Package cleanup**: Remove build dependencies and caches
4. **Alpine base**: Use minimal Alpine Linux for smaller footprint
5. **Dependency optimization**: Install only required runtime dependencies

## 🛠️ Development Workflow

### Local Development

```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f app

# Access container shell
docker-compose exec app bash

# Run tests
docker-compose exec app python -m pytest
```

### Hot Reload Development

The development image supports hot reload for faster development:

```bash
# Development with volume mounts
docker run -v $(pwd)/app:/app/app -p 8000:8000 slidegenie/backend:dev
```

## 🚀 Production Deployment

### Environment Setup

1. Copy and configure environment:
```bash
cp .env.production .env
# Edit .env with your production values
```

2. Set up data directories:
```bash
sudo mkdir -p /opt/slidegenie/data/{postgres,redis,minio,logs,uploads,exports}
sudo chown -R 1000:1000 /opt/slidegenie/data
```

3. Deploy with monitoring:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Production Features

- **Load balancing**: Traefik reverse proxy with SSL termination
- **Monitoring**: Prometheus + Grafana dashboards
- **High availability**: Multiple workers and health checks
- **Data persistence**: Proper volume management
- **Security**: TLS encryption, network isolation
- **Backup**: Automated backup strategies

## 📈 Monitoring and Observability

### Health Checks

All containers include comprehensive health checks:

```bash
# Check container health
docker ps --filter "health=healthy"

# View health check logs
docker inspect --format='{{json .State.Health}}' container_name
```

### Metrics Collection

Prometheus metrics available at:
- Application metrics: `http://localhost:8000/metrics`
- Container metrics: `http://localhost:8080/metrics` (cAdvisor)
- System metrics: `http://localhost:9100/metrics` (Node Exporter)

### Grafana Dashboards

Access monitoring dashboards at `http://localhost:3000`:
- Application Performance Dashboard
- Infrastructure Monitoring Dashboard
- Security Metrics Dashboard
- Business Metrics Dashboard

## 🔍 Troubleshooting

### Common Issues

#### Build Failures

```bash
# Clear build cache
docker builder prune -a

# Check buildx
docker buildx ls

# Debug build
docker buildx build --progress=plain .
```

#### Runtime Issues

```bash
# Check container logs
docker-compose logs app

# Inspect container
docker-compose exec app bash

# Check resource usage
docker stats
```

#### Permission Issues

```bash
# Fix volume permissions
sudo chown -R 1000:1000 /path/to/volumes

# Check SELinux context (if applicable)
ls -laZ /path/to/volumes
```

### Performance Tuning

#### Memory Optimization

```bash
# Set memory limits
docker run -m 2g slidegenie/backend:latest

# Monitor memory usage
docker stats --no-stream
```

#### CPU Optimization

```bash
# Set CPU limits
docker run --cpus="2.0" slidegenie/backend:latest

# CPU pinning for performance
docker run --cpuset-cpus="0,1" slidegenie/backend:latest
```

## 🔐 Security Best Practices

### Container Security Checklist

- [ ] Non-root user configured
- [ ] Minimal base image used
- [ ] No secrets in image layers
- [ ] Security scanning passed
- [ ] Regular base image updates
- [ ] Proper capability management
- [ ] Network segmentation implemented
- [ ] Resource limits configured

### Security Scanning Integration

```bash
# Daily vulnerability scan
0 2 * * * /path/to/scripts/security-scan.sh

# Pre-deployment scan
./scripts/build-images.sh --scan --version $(git describe --tags)
```

## 📝 Maintenance

### Regular Updates

1. **Base image updates**: Monthly security updates
2. **Dependency updates**: Weekly dependency scanning
3. **Security patches**: Immediate critical vulnerability patches
4. **Cleanup**: Weekly removal of unused images and containers

### Backup Strategy

```bash
# Database backup
docker-compose exec postgres pg_dump -U slidegenie slidegenie > backup.sql

# Volume backup
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## 🤝 Contributing

When contributing to the containerization setup:

1. Test all build variants
2. Run security scans
3. Update documentation
4. Validate production deployment
5. Submit PR with container test results

## 📚 Additional Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Container Security Guide](https://kubernetes.io/docs/concepts/security/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Cosign Documentation](https://docs.sigstore.dev/cosign/overview/)
- [Prometheus Monitoring](https://prometheus.io/docs/)

---

For questions or issues, please refer to the troubleshooting section or open an issue in the repository.