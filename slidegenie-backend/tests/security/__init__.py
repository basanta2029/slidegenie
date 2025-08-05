"""
SlideGenie Security Testing Suite.

Comprehensive security testing for:
- SQL Injection
- Cross-Site Scripting (XSS)
- File Upload vulnerabilities
- Authentication & Authorization
- API Security
- Penetration Testing
- OWASP Compliance
"""

from .security_test_utils import (
    VulnerabilityScanner,
    FuzzingGenerator,
    SecurityReportGenerator,
    OWASPComplianceChecker,
    VulnerabilityReport,
    VulnerabilityType
)

from .test_penetration_suite import PenetrationTestSuite

__all__ = [
    'VulnerabilityScanner',
    'FuzzingGenerator',
    'SecurityReportGenerator',
    'OWASPComplianceChecker',
    'VulnerabilityReport',
    'VulnerabilityType',
    'PenetrationTestSuite',
]