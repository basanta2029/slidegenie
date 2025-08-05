"""
Main performance test runner for SlideGenie.

This script orchestrates running different performance test scenarios
with various load profiles and configurations.
"""
import os
import sys
import subprocess
import time
import json
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from config import LoadProfile, config
from monitoring import PerformanceMonitor, AlertManager
from analyze_results import ResultAnalyzer


class PerformanceTestRunner:
    """Orchestrate performance test execution."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.base_url
        self.results_dir = Path("tests/performance/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Test scenarios mapping
        self.scenarios = {
            "generation": "tests.performance.scenarios.concurrent_generation",
            "upload": "tests.performance.scenarios.file_upload", 
            "export": "tests.performance.scenarios.export_queue",
            "websocket": "tests.performance.scenarios.websocket_scaling",
            "mixed": "tests.performance.scenarios.mixed_workload",
            "database": "tests.performance.scenarios.database_performance"
        }
        
        # Initialize components
        self.monitor: Optional[PerformanceMonitor] = None
        self.alert_manager = AlertManager({
            "cpu_percent": 90,
            "memory_mb": 8192,
            "error_rate_percent": 5,
            "response_time_p95_ms": 5000
        })
        
    def run_test(
        self,
        scenario: str,
        profile: LoadProfile = LoadProfile.DEVELOPMENT,
        duration: Optional[str] = None,
        monitor: bool = True
    ) -> Dict[str, Any]:
        """Run a specific performance test scenario."""
        if scenario not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(self.scenarios.keys())}")
            
        # Get load profile configuration
        profile_config = config.get_profile(profile)
        
        # Build Locust command
        locust_file = self.scenarios[scenario]
        
        cmd = [
            "locust",
            "-f", f"-",  # Read from stdin
            "--headless",
            "--host", self.base_url,
            "--users", str(profile_config["users"]),
            "--spawn-rate", str(profile_config["spawn_rate"]),
            "--run-time", duration or profile_config["run_time"],
            "--html", f"{self.results_dir}/{scenario}_{profile.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "--csv", f"{self.results_dir}/{scenario}_{profile.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        ]
        
        # Add custom settings
        if scenario == "websocket":
            # WebSocket tests need special handling
            cmd.extend(["--class-picker"])
            
        print(f"\n🚀 Starting {scenario} test with {profile.value} profile")
        print(f"   Users: {profile_config['users']}")
        print(f"   Spawn rate: {profile_config['spawn_rate']}/s")
        print(f"   Duration: {duration or profile_config['run_time']}")
        
        # Start monitoring if enabled
        monitor_task = None
        if monitor:
            monitor_task = asyncio.create_task(self._run_monitoring())
            
        # Import the test module dynamically
        import_stmt = f"from {locust_file} import *"
        
        try:
            # Run Locust test
            start_time = time.time()
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send the import statement to stdin
            stdout, stderr = process.communicate(input=import_stmt)
            
            if process.returncode != 0:
                print(f"❌ Test failed with return code: {process.returncode}")
                print(f"Error output: {stderr}")
                return {"success": False, "error": stderr}
                
            duration_seconds = time.time() - start_time
            
            print(f"✅ Test completed in {duration_seconds:.1f} seconds")
            
            # Stop monitoring
            if monitor_task:
                self.monitor.running = False
                asyncio.run(monitor_task)
                
            # Analyze results
            analyzer = ResultAnalyzer()
            report = analyzer.analyze_latest_test(scenario)
            
            # Check alerts
            if self.monitor:
                summary = self.monitor.get_summary()
                self.alert_manager.check_metrics(summary)
                alerts = self.alert_manager.get_alerts()
                
                if alerts:
                    print(f"\n⚠️  {len(alerts)} alerts generated during test:")
                    for alert in alerts[:5]:  # Show first 5 alerts
                        print(f"   - {alert['message']}")
                        
            return {
                "success": True,
                "scenario": scenario,
                "profile": profile.value,
                "duration": duration_seconds,
                "report": report,
                "alerts": self.alert_manager.get_alerts() if monitor else []
            }
            
        except Exception as e:
            print(f"❌ Error running test: {e}")
            return {"success": False, "error": str(e)}
            
    async def _run_monitoring(self):
        """Run performance monitoring during test."""
        db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/slidegenie")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        self.monitor = PerformanceMonitor(
            api_base_url=self.base_url,
            db_url=db_url,
            redis_url=redis_url
        )
        
        try:
            await self.monitor.start()
        except Exception as e:
            print(f"Monitoring error: {e}")
        finally:
            if self.monitor:
                # Export monitoring data
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.monitor.export_metrics(
                    f"{self.results_dir}/monitoring_{timestamp}.json"
                )
                await self.monitor.stop()
                
    def run_suite(
        self,
        scenarios: List[str],
        profile: LoadProfile = LoadProfile.STAGING
    ) -> Dict[str, Any]:
        """Run a suite of performance tests."""
        print(f"\n🔥 Running performance test suite with {profile.value} profile")
        print(f"   Scenarios: {', '.join(scenarios)}")
        
        results = {}
        start_time = time.time()
        
        for scenario in scenarios:
            print(f"\n{'='*60}")
            result = self.run_test(scenario, profile)
            results[scenario] = result
            
            # Brief pause between tests
            if scenario != scenarios[-1]:
                print("\n⏸️  Pausing 30 seconds before next test...")
                time.sleep(30)
                
        total_duration = time.time() - start_time
        
        # Generate summary report
        analyzer = ResultAnalyzer()
        dashboard_path = analyzer.generate_summary_dashboard()
        
        print(f"\n{'='*60}")
        print(f"✅ Test suite completed in {total_duration/60:.1f} minutes")
        print(f"📊 Dashboard generated: {dashboard_path}")
        
        # Summary statistics
        successful = sum(1 for r in results.values() if r.get("success"))
        print(f"\n📈 Summary:")
        print(f"   Successful: {successful}/{len(scenarios)}")
        
        for scenario, result in results.items():
            if result.get("success") and "report" in result:
                report = result["report"]
                print(f"\n   {scenario}:")
                print(f"     Success rate: {report.success_rate:.1f}%")
                print(f"     Throughput: {report.throughput_rps:.0f} RPS")
                
        return {
            "scenarios": results,
            "total_duration": total_duration,
            "dashboard": dashboard_path
        }
        
    def run_regression_test(self) -> bool:
        """Run regression tests comparing against baseline."""
        baseline_file = self.results_dir / "performance_baseline.json"
        
        if not baseline_file.exists():
            print("⚠️  No baseline found. Running tests to establish baseline...")
            self._create_baseline()
            return True
            
        # Load baseline
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
            
        # Run key scenarios
        scenarios = ["generation", "upload", "export", "database"]
        current_results = {}
        
        for scenario in scenarios:
            result = self.run_test(scenario, LoadProfile.STAGING, duration="5m")
            if result.get("success"):
                current_results[scenario] = {
                    "success_rate": result["report"].success_rate,
                    "throughput_rps": result["report"].throughput_rps,
                    "p95_response_time": self._get_p95_response_time(result["report"])
                }
                
        # Compare against baseline
        regressions = []
        
        for scenario, current in current_results.items():
            if scenario in baseline:
                base = baseline[scenario]
                
                # Check for regressions (10% tolerance)
                if current["success_rate"] < base["success_rate"] * 0.9:
                    regressions.append(
                        f"{scenario}: Success rate dropped from {base['success_rate']:.1f}% to {current['success_rate']:.1f}%"
                    )
                    
                if current["throughput_rps"] < base["throughput_rps"] * 0.9:
                    regressions.append(
                        f"{scenario}: Throughput dropped from {base['throughput_rps']:.0f} to {current['throughput_rps']:.0f} RPS"
                    )
                    
                if current["p95_response_time"] > base["p95_response_time"] * 1.1:
                    regressions.append(
                        f"{scenario}: P95 response time increased from {base['p95_response_time']:.0f}ms to {current['p95_response_time']:.0f}ms"
                    )
                    
        if regressions:
            print("\n❌ Performance regressions detected:")
            for regression in regressions:
                print(f"   - {regression}")
            return False
        else:
            print("\n✅ No performance regressions detected!")
            return True
            
    def _create_baseline(self):
        """Create performance baseline."""
        scenarios = ["generation", "upload", "export", "database"]
        baseline = {}
        
        for scenario in scenarios:
            result = self.run_test(scenario, LoadProfile.STAGING, duration="10m")
            if result.get("success"):
                baseline[scenario] = {
                    "success_rate": result["report"].success_rate,
                    "throughput_rps": result["report"].throughput_rps,
                    "p95_response_time": self._get_p95_response_time(result["report"]),
                    "timestamp": datetime.now().isoformat()
                }
                
        # Save baseline
        baseline_file = self.results_dir / "performance_baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2)
            
        print(f"\n📊 Baseline created: {baseline_file}")
        
    def _get_p95_response_time(self, report) -> float:
        """Extract P95 response time from report."""
        # Look for main response time metric
        for category, metrics in report.percentiles.items():
            for metric_name, values in metrics.items():
                if "completion_time" in metric_name or "response_time" in metric_name:
                    return values.get("p95", 0)
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run SlideGenie performance tests")
    
    parser.add_argument(
        "command",
        choices=["test", "suite", "regression", "monitor"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--scenario",
        choices=list(PerformanceTestRunner({}).scenarios.keys()),
        help="Test scenario to run"
    )
    
    parser.add_argument(
        "--profile",
        choices=[p.value for p in LoadProfile],
        default="development",
        help="Load profile to use"
    )
    
    parser.add_argument(
        "--duration",
        help="Test duration (e.g., 5m, 1h)"
    )
    
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for API"
    )
    
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Disable performance monitoring"
    )
    
    args = parser.parse_args()
    
    runner = PerformanceTestRunner(base_url=args.base_url)
    
    if args.command == "test":
        if not args.scenario:
            print("Error: --scenario required for test command")
            sys.exit(1)
            
        profile = LoadProfile(args.profile)
        result = runner.run_test(
            args.scenario,
            profile,
            args.duration,
            monitor=not args.no_monitor
        )
        
        sys.exit(0 if result.get("success") else 1)
        
    elif args.command == "suite":
        # Run default test suite
        scenarios = ["generation", "upload", "export", "mixed"]
        profile = LoadProfile(args.profile)
        
        runner.run_suite(scenarios, profile)
        
    elif args.command == "regression":
        # Run regression tests
        success = runner.run_regression_test()
        sys.exit(0 if success else 1)
        
    elif args.command == "monitor":
        # Run monitoring only
        print("Starting performance monitoring...")
        print("Press Ctrl+C to stop")
        
        try:
            asyncio.run(runner._run_monitoring())
        except KeyboardInterrupt:
            print("\nMonitoring stopped")


if __name__ == "__main__":
    main()