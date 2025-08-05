# SlideGenie Security Testing Suite

Comprehensive security testing framework for SlideGenie application, covering all major security vulnerabilities and compliance requirements.

## Overview

This security testing suite provides automated and manual testing capabilities for:

- **SQL Injection Prevention**
- **Cross-Site Scripting (XSS) Protection**
- **File Upload Security**
- **Authentication & Authorization**
- **API Security**
- **Penetration Testing**
- **OWASP Compliance Verification**

## Test Coverage

### 1. SQL Injection Tests (`test_sql_injection.py`)

Tests for various SQL injection vulnerabilities:
- Basic SQL injection attempts
- Parameterized query verification
- ORM injection attempts
- Second-order SQL injection
- Blind SQL injection detection
- Time-based injection attacks

```python
# Run SQL injection tests
pytest tests/security/test_sql_injection.py -v
```

### 2. XSS Prevention Tests (`test_xss_prevention.py`)

Comprehensive XSS testing:
- Input sanitization verification
- Output encoding tests
- DOM XSS prevention
- Stored XSS attempts
- CSP header validation
- React/Frontend XSS prevention

```python
# Run XSS tests
pytest tests/security/test_xss_prevention.py -v
```

### 3. File Upload Security (`test_file_upload_security.py`)

File upload vulnerability testing:
- Malicious file detection
- File type verification bypass attempts
- Path traversal attacks
- Zip bomb detection
- Image metadata exploits
- File size limits
- Magic number validation

```python
# Run file upload tests
pytest tests/security/test_file_upload_security.py -v
```

### 4. Authentication & Authorization (`test_auth_security.py`)

Authentication security testing:
- JWT token manipulation
- Session hijacking attempts
- Privilege escalation tests
- Password policy enforcement
- Rate limiting verification
- OAuth security
- API key security

```python
# Run auth tests
pytest tests/security/test_auth_security.py -v
```

### 5. API Security (`test_api_security.py`)

API-level security testing:
- CORS policy testing
- API key security
- Request tampering
- XXE injection attempts
- SSRF vulnerability checks
- API versioning security
- Input validation
- Output filtering

```python
# Run API security tests
pytest tests/security/test_api_security.py -v
```

## Security Testing Utilities

### FuzzingGenerator

Generate fuzzing payloads for security testing:

```python
from tests.security.security_test_utils import FuzzingGenerator

fuzzer = FuzzingGenerator()

# Generate SQL injection payloads
sql_payloads = fuzzer.generate_sql_injection_payloads()

# Generate XSS payloads
xss_payloads = fuzzer.generate_xss_payloads()

# Generate random inputs
random_inputs = fuzzer.generate_random_inputs(count=100)
```

### VulnerabilityScanner

Automated vulnerability scanning:

```python
from tests.security.security_test_utils import VulnerabilityScanner

scanner = VulnerabilityScanner(base_url="http://localhost:8000")

# Scan specific endpoint
vulnerabilities = await scanner.scan_endpoint(
    endpoint="/api/v1/presentations",
    method="GET",
    auth_token="your-token"
)
```

### SecurityReportGenerator

Generate comprehensive security reports:

```python
from tests.security.security_test_utils import SecurityReportGenerator

generator = SecurityReportGenerator()

# Generate Markdown report
report = generator.generate_report(vulnerabilities)

# Export as JSON
json_report = generator.export_json(vulnerabilities)
```

## Penetration Testing Suite

Run complete penetration testing:

```python
from tests.security.test_penetration_suite import PenetrationTestSuite

# Initialize suite
suite = PenetrationTestSuite(base_url="http://localhost:8000")

# Run full scan
results = await suite.run_full_scan(auth_token="your-token")

# Results include:
# - vulnerabilities: List of found vulnerabilities
# - test_results: Pass/fail for each test category
# - report: Comprehensive Markdown report
# - compliance: OWASP compliance results
```

## Running All Security Tests

### Quick Security Check

```bash
# Run all security tests
pytest tests/security/ -v

# Run with coverage
pytest tests/security/ --cov=app --cov-report=html

# Run specific vulnerability type
pytest tests/security/ -k "sql_injection" -v
```

### Full Penetration Test

```bash
# Run complete penetration test suite
python -m pytest tests/security/test_penetration_suite.py::test_run_penetration_suite -v
```

### Continuous Security Testing

```bash
# Run security tests in CI/CD pipeline
pytest tests/security/ --junit-xml=security-report.xml
```

## Security Test Configuration

### Environment Variables

```bash
# API base URL for testing
SECURITY_TEST_BASE_URL=http://localhost:8000

# Authentication token for protected endpoints
SECURITY_TEST_AUTH_TOKEN=your-test-token

# Enable/disable destructive tests
SECURITY_TEST_DESTRUCTIVE=false

# Report output directory
SECURITY_TEST_REPORTS_DIR=./security-reports
```

### Custom Test Configuration

Create `security_test_config.py`:

```python
SECURITY_TEST_CONFIG = {
    "base_url": "http://localhost:8000",
    "timeout": 30,
    "max_concurrent_requests": 10,
    "fuzzing_iterations": 100,
    "report_format": "markdown",  # or "json", "html"
    "owasp_compliance_level": "strict",
    "excluded_endpoints": [
        "/api/v1/health",
        "/api/v1/metrics"
    ]
}
```

## OWASP Compliance

The security tests verify compliance with:

- **OWASP Top 10 (2021)**
  - A01: Broken Access Control
  - A02: Cryptographic Failures
  - A03: Injection
  - A04: Insecure Design
  - A05: Security Misconfiguration
  - A06: Vulnerable and Outdated Components
  - A07: Identification and Authentication Failures
  - A08: Software and Data Integrity Failures
  - A09: Security Logging and Monitoring Failures
  - A10: Server-Side Request Forgery (SSRF)

- **OWASP API Security Top 10**
- **OWASP Authentication Cheat Sheet**
- **OWASP Session Management Cheat Sheet**

## Security Best Practices

1. **Run Security Tests Regularly**
   - Before each release
   - After major changes
   - As part of CI/CD pipeline

2. **Review Test Results**
   - Address critical vulnerabilities immediately
   - Plan remediation for lower severity issues
   - Update tests for new attack vectors

3. **Keep Tests Updated**
   - Add new test cases for discovered vulnerabilities
   - Update payloads with latest attack techniques
   - Follow security advisories

4. **Integration with Development**
   - Run subset of tests during development
   - Full suite before deployment
   - Automated scanning in staging

## Troubleshooting

### Common Issues

1. **Tests Timing Out**
   ```python
   # Increase timeout in pytest.ini
   [pytest]
   timeout = 300
   ```

2. **Rate Limiting During Tests**
   ```python
   # Add delays between requests
   import time
   time.sleep(0.5)  # Add to test loops
   ```

3. **Authentication Issues**
   ```python
   # Ensure valid test token
   auth_token = get_test_auth_token()
   ```

## Contributing

When adding new security tests:

1. Follow existing test structure
2. Add comprehensive documentation
3. Include remediation suggestions
4. Update OWASP mapping
5. Add to penetration test suite

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [CWE Database](https://cwe.mitre.org/)
- [NIST Vulnerability Database](https://nvd.nist.gov/)