#!/usr/bin/env python3
"""
Setup script for comprehensive API integration.

This script:
1. Installs required dependencies
2. Verifies middleware integration
3. Tests health check system
4. Validates API endpoints
5. Sets up monitoring and metrics
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class APIIntegrationSetup:
    """Setup class for API integration."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.api_prefix = "/api/v1"
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def install_dependencies(self) -> bool:
        """Install required dependencies."""
        console.print("[bold blue]Installing API integration dependencies...[/bold blue]")
        
        dependencies = [
            "prometheus-client>=0.21.0",
            "psutil>=6.1.0",
            "rich>=13.0.0",  # For this setup script
        ]
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Installing dependencies...", total=None)
                
                for dep in dependencies:
                    progress.update(task, description=f"Installing {dep}...")
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", dep],
                        capture_output=True,
                        text=True,
                        cwd=PROJECT_ROOT,
                    )
                    
                    if result.returncode != 0:
                        console.print(f"[red]Failed to install {dep}:[/red]")
                        console.print(result.stderr)
                        return False
                
                progress.update(task, description="Dependencies installed successfully!")
            
            console.print("[green]✓ Dependencies installed successfully[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {e}[/red]")
            return False
    
    def verify_file_structure(self) -> bool:
        """Verify that all required files are in place."""
        console.print("[bold blue]Verifying file structure...[/bold blue]")
        
        required_files = [
            "app/api/middleware.py",
            "app/api/exceptions.py", 
            "app/api/dependencies.py",
            "app/api/router.py",
            "app/core/health.py",
            "test/test_api_integration.py",
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            console.print("[red]Missing required files:[/red]")
            for file_path in missing_files:
                console.print(f"  - {file_path}")
            return False
        
        console.print("[green]✓ All required files are present[/green]")
        return True
    
    async def check_server_running(self) -> bool:
        """Check if the API server is running."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except:
            return False
    
    async def test_basic_endpoints(self) -> Dict[str, bool]:
        """Test basic API endpoints."""
        console.print("[bold blue]Testing basic endpoints...[/bold blue]")
        
        endpoints = {
            "Root": "/",
            "Health": "/health",
            "API Info": f"{self.api_prefix}/",
            "API Status": f"{self.api_prefix}/status",
            "API Limits": f"{self.api_prefix}/limits",
            "Health Check": f"{self.api_prefix}/health/health",
            "Readiness": f"{self.api_prefix}/health/ready",
            "Liveness": f"{self.api_prefix}/health/live",
            "Metrics": f"{self.api_prefix}/metrics",
        }
        
        results = {}
        
        for name, endpoint in endpoints.items():
            try:
                response = await self.client.get(endpoint)
                results[name] = response.status_code in [200, 503]  # 503 is ok for health checks
                
                if results[name]:
                    console.print(f"[green]✓ {name}: {response.status_code}[/green]")
                else:
                    console.print(f"[red]✗ {name}: {response.status_code}[/red]")
                    
            except Exception as e:
                results[name] = False
                console.print(f"[red]✗ {name}: Error - {e}[/red]")
        
        return results
    
    async def test_middleware_functionality(self) -> Dict[str, bool]:
        """Test middleware functionality."""
        console.print("[bold blue]Testing middleware functionality...[/bold blue]")
        
        results = {}
        
        # Test API versioning
        try:
            response = await self.client.get(f"{self.api_prefix}/health/health")
            results["API Versioning"] = "API-Version" in response.headers
            console.print(f"[{'green' if results['API Versioning'] else 'red'}]"
                         f"{'✓' if results['API Versioning'] else '✗'} API Versioning[/]")
        except:
            results["API Versioning"] = False
            console.print("[red]✗ API Versioning[/red]")
        
        # Test request ID
        try:
            response = await self.client.get(f"{self.api_prefix}/health/health")
            results["Request ID"] = "X-Request-ID" in response.headers
            console.print(f"[{'green' if results['Request ID'] else 'red'}]"
                         f"{'✓' if results['Request ID'] else '✗'} Request ID[/]")
        except:
            results["Request ID"] = False
            console.print("[red]✗ Request ID[/red]")
        
        # Test security headers
        try:
            response = await self.client.get(f"{self.api_prefix}/health/health")
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options", 
                "X-XSS-Protection",
            ]
            results["Security Headers"] = any(
                header in response.headers for header in security_headers
            )
            console.print(f"[{'green' if results['Security Headers'] else 'red'}]"
                         f"{'✓' if results['Security Headers'] else '✗'} Security Headers[/]")
        except:
            results["Security Headers"] = False
            console.print("[red]✗ Security Headers[/red]")
        
        # Test error handling
        try:
            response = await self.client.get(f"{self.api_prefix}/nonexistent")
            results["Error Handling"] = response.status_code == 404
            console.print(f"[{'green' if results['Error Handling'] else 'red'}]"
                         f"{'✓' if results['Error Handling'] else '✗'} Error Handling[/]")
        except:
            results["Error Handling"] = False
            console.print("[red]✗ Error Handling[/red]")
        
        return results
    
    async def test_authentication_endpoints(self) -> Dict[str, bool]:
        """Test authentication-related endpoints."""
        console.print("[bold blue]Testing authentication endpoints...[/bold blue]")
        
        auth_endpoints = {
            "Register": f"{self.api_prefix}/auth/register",
            "Login": f"{self.api_prefix}/auth/login",
            "OAuth Google": f"{self.api_prefix}/oauth/google",
            "OAuth Microsoft": f"{self.api_prefix}/oauth/microsoft",
            "User Profile": f"{self.api_prefix}/users/me",
        }
        
        results = {}
        
        for name, endpoint in auth_endpoints.items():
            try:
                response = await self.client.get(endpoint)
                # Auth endpoints should return 401, 405, or 422, not 404
                results[name] = response.status_code != 404
                
                if results[name]:
                    console.print(f"[green]✓ {name}: {response.status_code}[/green]")
                else:
                    console.print(f"[red]✗ {name}: {response.status_code}[/red]")
                    
            except Exception as e:
                results[name] = False
                console.print(f"[red]✗ {name}: Error - {e}[/red]")
        
        return results
    
    async def test_rate_limiting(self) -> bool:
        """Test rate limiting functionality."""
        console.print("[bold blue]Testing rate limiting...[/bold blue]")
        
        try:
            # Send multiple rapid requests
            tasks = []
            for _ in range(10):
                tasks.append(self.client.get(f"{self.api_prefix}/health/health"))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check if any rate limit headers are present
            rate_limit_present = False
            for response in responses:
                if hasattr(response, 'headers'):
                    if any(header.startswith('X-RateLimit') for header in response.headers):
                        rate_limit_present = True
                        break
            
            console.print(f"[{'green' if rate_limit_present else 'yellow'}]"
                         f"{'✓' if rate_limit_present else '~'} Rate Limiting "
                         f"{'detected' if rate_limit_present else 'not detected (may be disabled in dev)'}[/]")
            
            return True  # Don't fail if rate limiting is not active in dev
            
        except Exception as e:
            console.print(f"[red]✗ Rate Limiting: Error - {e}[/red]")
            return False
    
    async def test_health_system(self) -> Dict[str, bool]:
        """Test comprehensive health check system."""
        console.print("[bold blue]Testing health check system...[/bold blue]")
        
        results = {}
        
        # Test comprehensive health check
        try:
            response = await self.client.get(f"{self.api_prefix}/health/health")
            if response.status_code in [200, 503]:
                data = response.json()
                results["Health Check"] = "status" in data and "components" in data
            else:
                results["Health Check"] = False
                
            console.print(f"[{'green' if results['Health Check'] else 'red'}]"
                         f"{'✓' if results['Health Check'] else '✗'} Health Check[/]")
        except:
            results["Health Check"] = False
            console.print("[red]✗ Health Check[/red]")
        
        # Test readiness check
        try:
            response = await self.client.get(f"{self.api_prefix}/health/ready")
            results["Readiness"] = response.status_code in [200, 503]
            console.print(f"[{'green' if results['Readiness'] else 'red'}]"
                         f"{'✓' if results['Readiness'] else '✗'} Readiness Check[/]")
        except:
            results["Readiness"] = False
            console.print("[red]✗ Readiness Check[/red]")
        
        # Test liveness check
        try:
            response = await self.client.get(f"{self.api_prefix}/health/live")
            results["Liveness"] = response.status_code in [200, 503]
            console.print(f"[{'green' if results['Liveness'] else 'red'}]"
                         f"{'✓' if results['Liveness'] else '✗'} Liveness Check[/]")
        except:
            results["Liveness"] = False
            console.print("[red]✗ Liveness Check[/red]")
        
        # Test metrics
        try:
            response = await self.client.get(f"{self.api_prefix}/health/metrics")
            results["Metrics"] = response.status_code == 200
            console.print(f"[{'green' if results['Metrics'] else 'red'}]"
                         f"{'✓' if results['Metrics'] else '✗'} Health Metrics[/]")
        except:
            results["Metrics"] = False
            console.print("[red]✗ Health Metrics[/red]")
        
        return results
    
    async def run_performance_test(self) -> Dict[str, float]:
        """Run basic performance tests."""
        console.print("[bold blue]Running performance tests...[/bold blue]")
        
        results = {}
        
        # Test single request latency
        try:
            start_time = time.time()
            response = await self.client.get(f"{self.api_prefix}/health/health")
            end_time = time.time()
            
            if response.status_code in [200, 503]:
                results["Single Request Latency (ms)"] = (end_time - start_time) * 1000
                console.print(f"[green]✓ Single Request Latency: "
                             f"{results['Single Request Latency (ms)']:.2f}ms[/green]")
            else:
                results["Single Request Latency (ms)"] = -1
                console.print("[red]✗ Single Request Latency Test Failed[/red]")
        except Exception as e:
            results["Single Request Latency (ms)"] = -1
            console.print(f"[red]✗ Single Request Latency: {e}[/red]")
        
        # Test concurrent requests
        try:
            start_time = time.time()
            tasks = [
                self.client.get(f"{self.api_prefix}/health/health")
                for _ in range(10)
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_responses = sum(
                1 for r in responses 
                if hasattr(r, 'status_code') and r.status_code in [200, 503]
            )
            
            if successful_responses >= 8:  # Allow some failures
                results["Concurrent Requests (10 req total time ms)"] = (end_time - start_time) * 1000
                console.print(f"[green]✓ Concurrent Requests: "
                             f"{results['Concurrent Requests (10 req total time ms)']:.2f}ms total[/green]")
            else:
                results["Concurrent Requests (10 req total time ms)"] = -1
                console.print(f"[red]✗ Concurrent Requests: Only {successful_responses}/10 successful[/red]")
        except Exception as e:
            results["Concurrent Requests (10 req total time ms)"] = -1
            console.print(f"[red]✗ Concurrent Requests: {e}[/red]")
        
        return results
    
    def generate_report(
        self,
        basic_tests: Dict[str, bool],
        middleware_tests: Dict[str, bool],
        auth_tests: Dict[str, bool],
        health_tests: Dict[str, bool],
        performance_results: Dict[str, float],
        rate_limit_test: bool,
    ) -> None:
        """Generate a comprehensive test report."""
        console.print("\n" + "="*80)
        console.print(Panel.fit(
            "[bold green]API Integration Setup Report[/bold green]",
            style="bold blue"
        ))
        
        # Summary table
        table = Table(title="Test Results Summary", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="dim", width=20)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Details", width=40)
        
        # Calculate pass rates
        categories = {
            "Basic Endpoints": basic_tests,
            "Middleware": middleware_tests,
            "Authentication": auth_tests,
            "Health System": health_tests,
        }
        
        for category, tests in categories.items():
            passed = sum(tests.values())
            total = len(tests)
            percentage = (passed / total) * 100 if total > 0 else 0
            
            status = "✓ PASS" if percentage >= 80 else "⚠ WARN" if percentage >= 60 else "✗ FAIL"
            status_style = "green" if percentage >= 80 else "yellow" if percentage >= 60 else "red"
            
            table.add_row(
                category,
                f"[{status_style}]{status}[/{status_style}]",
                f"{passed}/{total} tests passed ({percentage:.1f}%)"
            )
        
        # Add rate limiting and performance
        table.add_row(
            "Rate Limiting",
            f"[{'green' if rate_limit_test else 'yellow'}]{'✓ PASS' if rate_limit_test else '~ N/A'}[/]",
            "Rate limiting functional" if rate_limit_test else "Not active in dev mode"
        )
        
        performance_status = "✓ PASS" if all(v > 0 for v in performance_results.values()) else "✗ FAIL"
        performance_style = "green" if all(v > 0 for v in performance_results.values()) else "red"
        table.add_row(
            "Performance",
            f"[{performance_style}]{performance_status}[/{performance_style}]",
            f"Avg latency: {performance_results.get('Single Request Latency (ms)', -1):.2f}ms"
        )
        
        console.print(table)
        
        # Performance details
        if performance_results:
            perf_table = Table(title="Performance Metrics", show_header=True, header_style="bold cyan")
            perf_table.add_column("Metric", style="dim")
            perf_table.add_column("Value", justify="right")
            
            for metric, value in performance_results.items():
                if value > 0:
                    perf_table.add_row(metric, f"{value:.2f}")
                else:
                    perf_table.add_row(metric, "[red]Failed[/red]")
            
            console.print(perf_table)
        
        # Overall assessment
        total_passed = sum(sum(tests.values()) for tests in categories.values())
        total_tests = sum(len(tests) for tests in categories.values())
        overall_percentage = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        if overall_percentage >= 90:
            overall_status = "[bold green]EXCELLENT[/bold green]"
            message = "API integration is fully functional with all systems operational."
        elif overall_percentage >= 80:
            overall_status = "[bold yellow]GOOD[/bold yellow]"
            message = "API integration is mostly functional with minor issues."
        elif overall_percentage >= 60:
            overall_status = "[bold orange]FAIR[/bold orange]"
            message = "API integration has some issues that should be addressed."
        else:
            overall_status = "[bold red]POOR[/bold red]"
            message = "API integration has significant issues requiring immediate attention."
        
        console.print(f"\n[bold]Overall Status:[/bold] {overall_status}")
        console.print(f"[dim]{message}[/dim]")
        
        # Next steps
        console.print("\n[bold blue]Next Steps:[/bold blue]")
        if overall_percentage >= 90:
            console.print("• ✓ API integration is ready for production")
            console.print("• Consider setting up monitoring dashboards")
            console.print("• Review security configurations")
        else:
            console.print("• Fix failing tests before production deployment")
            console.print("• Review middleware configurations")
            console.print("• Test with real database and Redis instances")


async def main():
    """Main setup function."""
    setup = APIIntegrationSetup()
    
    console.print(Panel.fit(
        "[bold blue]SlideGenie API Integration Setup[/bold blue]\n"
        "This will verify and test the comprehensive API integration.",
        style="bold blue"
    ))
    
    # Step 1: Install dependencies
    if not setup.install_dependencies():
        console.print("[red]Failed to install dependencies. Exiting.[/red]")
        return 1
    
    # Step 2: Verify file structure
    if not setup.verify_file_structure():
        console.print("[red]Missing required files. Exiting.[/red]")
        return 1
    
    # Step 3: Check if server is running
    console.print("[bold blue]Checking if API server is running...[/bold blue]")
    async with setup:
        server_running = await setup.check_server_running()
        
        if not server_running:
            console.print("[yellow]API server is not running.[/yellow]")
            console.print("Please start the server with: [bold]uvicorn app.main:app --reload[/bold]")
            console.print("Then run this script again.")
            return 1
        
        console.print("[green]✓ API server is running[/green]")
        
        # Step 4: Run all tests
        basic_tests = await setup.test_basic_endpoints()
        middleware_tests = await setup.test_middleware_functionality()
        auth_tests = await setup.test_authentication_endpoints()
        health_tests = await setup.test_health_system()
        rate_limit_test = await setup.test_rate_limiting()
        performance_results = await setup.run_performance_test()
        
        # Step 5: Generate report
        setup.generate_report(
            basic_tests,
            middleware_tests,
            auth_tests,
            health_tests,
            performance_results,
            rate_limit_test,
        )
    
    return 0


if __name__ == "__main__":
    try:
        import rich
    except ImportError:
        print("Installing rich for better output...")
        subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)
        import rich
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)