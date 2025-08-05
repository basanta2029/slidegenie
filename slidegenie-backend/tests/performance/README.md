# SlideGenie Performance Testing Framework

Comprehensive performance testing suite for SlideGenie using Locust, with real-time monitoring, result analysis, and automated regression detection.

## Overview

This performance testing framework provides:

- **Load Testing Scenarios**: Concurrent generation, file uploads, export queue, WebSocket scaling, database performance
- **User Simulation**: Realistic user behavior patterns with different personas
- **Real-time Monitoring**: System and application metrics collection during tests
- **Result Analysis**: Automated analysis with recommendations and visualizations
- **Regression Detection**: Compare results against baseline performance
- **Grafana Integration**: Pre-configured dashboards for monitoring

## Prerequisites

```bash
# Install required packages
pip install locust pandas matplotlib seaborn prometheus-client asyncpg aiohttp psutil

# For monitoring (optional)
docker run -d -p 9090:9090 prom/prometheus
docker run -d -p 3000:3000 grafana/grafana
```

## Quick Start

### Run a Single Test

```bash
# Run generation performance test with development profile
python tests/performance/run_tests.py test --scenario generation --profile development

# Run file upload test with production profile for 30 minutes
python tests/performance/run_tests.py test --scenario upload --profile production --duration 30m

# Run WebSocket scaling test
python tests/performance/run_tests.py test --scenario websocket --profile stress
```

### Run Test Suite

```bash
# Run standard test suite
python tests/performance/run_tests.py suite --profile staging

# Run with custom base URL
python tests/performance/run_tests.py suite --base-url https://api.slidegenie.com
```

### Run Regression Tests

```bash
# Check for performance regressions
python tests/performance/run_tests.py regression
```

## Test Scenarios

### 1. Concurrent Generation (`generation`)
Tests AI-powered presentation generation under load:
- Multiple simultaneous generation requests
- Document-based generation
- AI suggestion processing
- Bulk slide generation

### 2. File Upload (`upload`)
Tests file upload and processing performance:
- Small files (1MB)
- Medium files (10MB)
- Large files (50MB)
- Huge files (100MB)
- Multipart uploads
- Concurrent uploads

### 3. Export Queue (`export`)
Tests export system performance:
- PPTX exports
- PDF exports
- Beamer/LaTeX exports
- Google Slides exports
- Bulk exports
- Queue stress testing

### 4. WebSocket Scaling (`websocket`)
Tests real-time collaboration:
- Connection establishment
- Message throughput
- Cursor tracking
- Collaborative editing
- Reconnection handling
- Large message handling

### 5. Mixed Workload (`mixed`)
Simulates realistic user behavior:
- Browser persona (30%)
- Creator persona (25%)
- Collaborator persona (20%)
- Power user persona (10%)
- Reviewer persona (15%)

### 6. Database Performance (`database`)
Tests database query optimization:
- Simple queries
- Complex filters
- Full-text search
- Aggregations
- Join-heavy queries
- Pagination performance
- Cache effectiveness

## Load Profiles

### Development
- Users: 10
- Spawn rate: 2/s
- Duration: 2 minutes
- Wait time: 1-3 seconds

### Staging
- Users: 50
- Spawn rate: 5/s
- Duration: 10 minutes
- Wait time: 2-5 seconds

### Production
- Users: 100
- Spawn rate: 10/s
- Duration: 30 minutes
- Wait time: 3-8 seconds

### Stress
- Users: 500
- Spawn rate: 50/s
- Duration: 15 minutes
- Wait time: 1-2 seconds

### Spike
- Users: 1000
- Spawn rate: 100/s
- Duration: 5 minutes
- Wait time: 0.5-1 seconds

### Soak
- Users: 200
- Spawn rate: 10/s
- Duration: 2 hours
- Wait time: 5-10 seconds

## Monitoring

### Real-time Metrics
The framework collects:
- System metrics (CPU, memory, disk, network)
- Application metrics (active users, queue sizes, cache hit rates)
- Database metrics (connection pool, query performance)
- Custom metrics (AI token usage, file processing times)

### Prometheus Metrics
Exposed metrics include:
- `slidegenie_requests_total`
- `slidegenie_request_duration_seconds`
- `slidegenie_active_connections`
- `slidegenie_queue_size`
- `slidegenie_db_pool_size`
- `slidegenie_cache_hit_rate`

### Grafana Dashboards
Pre-configured dashboards in `grafana_dashboards/`:
- API Performance
- WebSocket Connections
- File Processing
- Database Queries
- Queue Metrics

## Result Analysis

### Generate Reports

```bash
# Analyze latest test results
python tests/performance/analyze_results.py generation --report

# Compare last 5 test runs
python tests/performance/analyze_results.py generation --compare 5

# Visualize specific metric
python tests/performance/analyze_results.py generation --visualize generation_completion_time

# Generate summary dashboard
python tests/performance/analyze_results.py generation --dashboard
```

### Performance Thresholds

Default thresholds (configurable in `config.py`):
- P50 response time: < 200ms
- P90 response time: < 500ms
- P95 response time: < 1000ms
- P99 response time: < 2000ms
- Error rate: < 1%
- Minimum throughput: 100 RPS

## Creating Custom Tests

### 1. Create Test Scenario

```python
# tests/performance/scenarios/custom_test.py
from locust import task
from ..base_user import BaseSlideGenieUser

class CustomTestUser(BaseSlideGenieUser):
    @task
    def my_custom_task(self):
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/custom-endpoint",
            name="Custom operation"
        )
```

### 2. Add to Runner

```python
# In run_tests.py
self.scenarios["custom"] = "tests.performance.scenarios.custom_test"
```

### 3. Run Test

```bash
python tests/performance/run_tests.py test --scenario custom
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install locust pandas matplotlib
          
      - name: Run regression tests
        run: |
          python tests/performance/run_tests.py regression
          
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: tests/performance/results/
```

## Best Practices

1. **Warm-up Period**: Allow 30-60 seconds for the system to warm up before collecting metrics

2. **Realistic Data**: Use production-like data sizes and content

3. **Network Conditions**: Test from similar network conditions as real users

4. **Monitoring**: Always run with monitoring enabled to catch system bottlenecks

5. **Baseline Updates**: Update performance baseline after significant optimizations

6. **Regular Testing**: Run regression tests nightly or before releases

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure API server is running
   - Check base URL configuration
   - Verify firewall settings

2. **Authentication Failures**
   - Create test users before running tests
   - Check credentials in configuration
   - Ensure auth endpoints are working

3. **High Error Rates**
   - Check server logs for errors
   - Reduce load to identify breaking point
   - Monitor system resources

4. **Inconsistent Results**
   - Ensure consistent test environment
   - Check for background processes
   - Use longer test durations

### Debug Mode

```bash
# Run with debug output
LOCUST_LOGLEVEL=DEBUG python tests/performance/run_tests.py test --scenario generation

# Monitor specific metrics
python tests/performance/monitoring.py --metric cpu_usage --interval 1
```

## Performance Optimization Tips

Based on test results, consider:

1. **API Response Times**
   - Implement caching strategies
   - Optimize database queries
   - Use connection pooling

2. **File Uploads**
   - Implement chunked uploads
   - Use CDN for static assets
   - Optimize file processing

3. **WebSocket Performance**
   - Implement message batching
   - Use binary protocols
   - Scale horizontally

4. **Database Performance**
   - Add appropriate indexes
   - Optimize complex queries
   - Implement query caching

5. **Queue Processing**
   - Scale workers horizontally
   - Implement priority queues
   - Monitor queue depths

## Contributing

When adding new performance tests:

1. Follow existing patterns in `base_user.py`
2. Add meaningful metrics collection
3. Include result analysis
4. Document test scenarios
5. Add to regression suite if critical

## License

See main project LICENSE file.