"""
Performance test result analysis and reporting.
"""
import json
import os
import glob
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PerformanceReport:
    """Performance test report."""
    test_name: str
    timestamp: str
    duration_seconds: float
    total_requests: int
    success_rate: float
    error_rate: float
    percentiles: Dict[str, Dict[str, float]]
    throughput_rps: float
    recommendations: List[str]
    

class ResultAnalyzer:
    """Analyze performance test results."""
    
    def __init__(self, results_dir: str = "tests/performance/results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def analyze_latest_test(self, test_type: str) -> PerformanceReport:
        """Analyze the latest test results for a given type."""
        # Find latest result file
        pattern = f"{test_type}_metrics_*.json"
        files = list(self.results_dir.glob(pattern))
        
        if not files:
            raise ValueError(f"No results found for test type: {test_type}")
            
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        
        return self.analyze_file(latest_file)
        
    def analyze_file(self, filepath: Path) -> PerformanceReport:
        """Analyze a specific result file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        # Extract test info from filename
        filename = filepath.stem
        parts = filename.split('_')
        test_name = '_'.join(parts[:-2])
        timestamp = parts[-2] + '_' + parts[-1]
        
        # Calculate metrics
        duration = data.get('duration_seconds', 0)
        metrics = data.get('metrics', {})
        errors = data.get('errors', {})
        
        # Calculate success rate
        total_requests = sum(m.get('count', 0) for m in metrics.values())
        total_errors = sum(errors.values())
        success_rate = (total_requests / (total_requests + total_errors) * 100) if total_requests > 0 else 0
        error_rate = 100 - success_rate
        
        # Calculate throughput
        throughput_rps = total_requests / duration if duration > 0 else 0
        
        # Extract key percentiles
        key_metrics = self._extract_key_metrics(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            metrics, errors, success_rate, throughput_rps
        )
        
        return PerformanceReport(
            test_name=test_name,
            timestamp=timestamp,
            duration_seconds=duration,
            total_requests=total_requests,
            success_rate=success_rate,
            error_rate=error_rate,
            percentiles=key_metrics,
            throughput_rps=throughput_rps,
            recommendations=recommendations
        )
        
    def _extract_key_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Extract key metrics and percentiles."""
        key_metrics = {}
        
        # Define metric categories
        categories = {
            'response_time': ['generation_completion_time', 'export_completion_time', 
                            'upload_time_medium', 'db_query_complex_filter'],
            'throughput': ['upload_throughput_mbps_medium', 'export_pdf_download_throughput_mbps'],
            'processing': ['file_processing_time', 'ai_tokens_used', 'slides_generated'],
            'database': ['db_query_simple_get', 'db_query_fulltext_search', 
                        'db_cache_speedup_ratio'],
            'websocket': ['websocket_connection_time', 'websocket_rtt']
        }
        
        for category, metric_names in categories.items():
            category_metrics = {}
            
            for metric_name in metric_names:
                if metric_name in metrics:
                    metric_data = metrics[metric_name]
                    category_metrics[metric_name] = {
                        'p50': metric_data.get('p50', 0),
                        'p90': metric_data.get('p90', 0),
                        'p95': metric_data.get('p95', 0),
                        'p99': metric_data.get('p99', 0),
                        'max': metric_data.get('max', 0)
                    }
                    
            if category_metrics:
                key_metrics[category] = category_metrics
                
        return key_metrics
        
    def _generate_recommendations(
        self,
        metrics: Dict[str, Any],
        errors: Dict[str, int],
        success_rate: float,
        throughput_rps: float
    ) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []
        
        # Check success rate
        if success_rate < 99:
            recommendations.append(
                f"⚠️ Success rate is {success_rate:.1f}%. Investigate errors: {list(errors.keys())}"
            )
            
        # Check response times
        slow_operations = []
        for metric_name, metric_data in metrics.items():
            if 'completion_time' in metric_name or 'query' in metric_name:
                p95 = metric_data.get('p95', 0)
                if p95 > 5000:  # 5 seconds
                    slow_operations.append((metric_name, p95))
                    
        if slow_operations:
            recommendations.append(
                f"🐌 Slow operations detected: " + 
                ", ".join(f"{op[0]} (P95: {op[1]:.0f}ms)" for op in slow_operations[:3])
            )
            
        # Check throughput
        if throughput_rps < 100:
            recommendations.append(
                f"📉 Low throughput: {throughput_rps:.1f} RPS. Consider scaling or optimization."
            )
            
        # Check database performance
        if 'db_cache_speedup_ratio' in metrics:
            cache_ratio = metrics['db_cache_speedup_ratio'].get('mean', 1)
            if cache_ratio < 2:
                recommendations.append(
                    f"💾 Low cache effectiveness (ratio: {cache_ratio:.1f}). Review caching strategy."
                )
                
        # Check file upload performance
        if 'upload_throughput_mbps_medium' in metrics:
            throughput = metrics['upload_throughput_mbps_medium'].get('mean', 0)
            if throughput < 10:  # Less than 10 Mbps
                recommendations.append(
                    f"📤 Slow upload throughput: {throughput:.1f} Mbps. Check network/storage."
                )
                
        # Check AI usage
        if 'ai_tokens_used' in metrics:
            avg_tokens = metrics['ai_tokens_used'].get('mean', 0)
            if avg_tokens > 10000:
                recommendations.append(
                    f"🤖 High AI token usage: {avg_tokens:.0f} avg. Consider prompt optimization."
                )
                
        # Add positive findings
        if success_rate >= 99.9:
            recommendations.append("✅ Excellent reliability with 99.9%+ success rate!")
            
        if throughput_rps > 500:
            recommendations.append(f"🚀 Great throughput: {throughput_rps:.0f} RPS!")
            
        return recommendations
        
    def compare_tests(
        self,
        test_type: str,
        num_tests: int = 5
    ) -> pd.DataFrame:
        """Compare multiple test runs."""
        pattern = f"{test_type}_metrics_*.json"
        files = sorted(
            self.results_dir.glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:num_tests]
        
        if not files:
            return pd.DataFrame()
            
        comparisons = []
        for file in files:
            report = self.analyze_file(file)
            comparisons.append({
                'timestamp': report.timestamp,
                'duration_s': report.duration_seconds,
                'requests': report.total_requests,
                'success_rate': report.success_rate,
                'throughput_rps': report.throughput_rps
            })
            
        return pd.DataFrame(comparisons)
        
    def generate_report(
        self,
        test_type: str,
        output_file: Optional[str] = None
    ) -> str:
        """Generate a comprehensive performance report."""
        report = self.analyze_latest_test(test_type)
        
        # Build report content
        content = f"""
# Performance Test Report: {report.test_name}

**Test Date:** {report.timestamp}  
**Duration:** {report.duration_seconds:.1f} seconds  
**Total Requests:** {report.total_requests:,}  
**Success Rate:** {report.success_rate:.2f}%  
**Error Rate:** {report.error_rate:.2f}%  
**Throughput:** {report.throughput_rps:.1f} RPS  

## Key Metrics

"""
        
        # Add percentile tables for each category
        for category, metrics in report.percentiles.items():
            content += f"### {category.replace('_', ' ').title()}\n\n"
            content += "| Metric | P50 | P90 | P95 | P99 | Max |\n"
            content += "|--------|-----|-----|-----|-----|-----|\n"
            
            for metric_name, values in metrics.items():
                short_name = metric_name.replace(f"{category}_", "").replace("_", " ")
                content += f"| {short_name} | "
                content += f"{values['p50']:.0f} | "
                content += f"{values['p90']:.0f} | "
                content += f"{values['p95']:.0f} | "
                content += f"{values['p99']:.0f} | "
                content += f"{values['max']:.0f} |\n"
                
            content += "\n"
            
        # Add recommendations
        content += "## Recommendations\n\n"
        for rec in report.recommendations:
            content += f"- {rec}\n"
            
        # Add comparison if available
        comparison_df = self.compare_tests(test_type, num_tests=5)
        if not comparison_df.empty:
            content += "\n## Historical Comparison\n\n"
            content += comparison_df.to_markdown(index=False)
            content += "\n"
            
        # Save report
        if output_file:
            with open(output_file, 'w') as f:
                f.write(content)
        else:
            output_file = self.results_dir / f"{test_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(output_file, 'w') as f:
                f.write(content)
                
        return str(output_file)
        
    def visualize_results(
        self,
        test_type: str,
        metric_name: str,
        output_dir: Optional[str] = None
    ):
        """Create visualizations for test results."""
        if not output_dir:
            output_dir = self.results_dir / "visualizations"
            output_dir.mkdir(exist_ok=True)
            
        # Load latest test data
        pattern = f"{test_type}_metrics_*.json"
        files = list(self.results_dir.glob(pattern))
        
        if not files:
            print(f"No results found for {test_type}")
            return
            
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        
        with open(latest_file, 'r') as f:
            data = json.load(f)
            
        metrics = data.get('metrics', {})
        
        if metric_name not in metrics:
            print(f"Metric {metric_name} not found")
            return
            
        metric_data = metrics[metric_name]
        
        # Create distribution plot
        plt.figure(figsize=(12, 6))
        
        # Percentile bar chart
        plt.subplot(1, 2, 1)
        percentiles = ['p50', 'p90', 'p95', 'p99']
        values = [metric_data.get(p, 0) for p in percentiles]
        
        bars = plt.bar(percentiles, values, color=['green', 'yellow', 'orange', 'red'])
        plt.title(f"{metric_name} - Percentiles")
        plt.ylabel("Time (ms)")
        plt.xlabel("Percentile")
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{value:.0f}', ha='center', va='bottom')
                    
        # Time series plot if available
        plt.subplot(1, 2, 2)
        # This would require storing time series data during the test
        plt.text(0.5, 0.5, "Time series data not available\nin current implementation",
                ha='center', va='center', transform=plt.gca().transAxes)
        plt.title(f"{metric_name} - Over Time")
        plt.xlabel("Time")
        plt.ylabel("Value")
        
        plt.tight_layout()
        
        # Save plot
        output_file = Path(output_dir) / f"{test_type}_{metric_name}_visualization.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Visualization saved to: {output_file}")
        
    def generate_summary_dashboard(self, output_file: str = "performance_dashboard.html"):
        """Generate an HTML dashboard with all test results."""
        # This would generate a comprehensive HTML dashboard
        # For now, we'll create a simple summary
        
        all_reports = []
        
        # Analyze all available test types
        for test_type in ['generation', 'file_upload', 'export_queue', 'websocket', 'mixed_workload', 'database']:
            try:
                report = self.analyze_latest_test(test_type)
                all_reports.append(report)
            except ValueError:
                continue
                
        if not all_reports:
            print("No test results found")
            return
            
        # Create HTML dashboard
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>SlideGenie Performance Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .test-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px 20px 10px 0; }
        .metric-value { font-size: 24px; font-weight: bold; }
        .metric-label { color: #666; font-size: 14px; }
        .good { color: green; }
        .warning { color: orange; }
        .bad { color: red; }
        .recommendations { background-color: #f0f0f0; padding: 10px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>SlideGenie Performance Test Dashboard</h1>
    <p>Generated: {timestamp}</p>
""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        for report in all_reports:
            status_class = "good" if report.success_rate >= 99 else "warning" if report.success_rate >= 95 else "bad"
            
            html_content += f"""
    <div class="test-card">
        <h2>{report.test_name.replace('_', ' ').title()}</h2>
        <div class="metric">
            <div class="metric-value {status_class}">{report.success_rate:.1f}%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.throughput_rps:.0f}</div>
            <div class="metric-label">RPS</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.total_requests:,}</div>
            <div class="metric-label">Total Requests</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.duration_seconds:.0f}s</div>
            <div class="metric-label">Duration</div>
        </div>
        
        <h3>Recommendations</h3>
        <div class="recommendations">
            <ul>
"""
            
            for rec in report.recommendations[:3]:  # Show top 3 recommendations
                html_content += f"                <li>{rec}</li>\n"
                
            html_content += """
            </ul>
        </div>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        output_path = self.results_dir / output_file
        with open(output_path, 'w') as f:
            f.write(html_content)
            
        print(f"Dashboard generated: {output_path}")
        return str(output_path)


def main():
    """Main entry point for result analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze performance test results")
    parser.add_argument("test_type", help="Type of test to analyze")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--visualize", help="Visualize specific metric")
    parser.add_argument("--dashboard", action="store_true", help="Generate summary dashboard")
    parser.add_argument("--compare", type=int, help="Compare last N test runs")
    
    args = parser.parse_args()
    
    analyzer = ResultAnalyzer()
    
    if args.dashboard:
        analyzer.generate_summary_dashboard()
    elif args.report:
        report_file = analyzer.generate_report(args.test_type)
        print(f"Report generated: {report_file}")
    elif args.visualize:
        analyzer.visualize_results(args.test_type, args.visualize)
    elif args.compare:
        df = analyzer.compare_tests(args.test_type, args.compare)
        print(df.to_string())
    else:
        report = analyzer.analyze_latest_test(args.test_type)
        print(f"\nTest: {report.test_name}")
        print(f"Success Rate: {report.success_rate:.2f}%")
        print(f"Throughput: {report.throughput_rps:.1f} RPS")
        print("\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")


if __name__ == "__main__":
    main()