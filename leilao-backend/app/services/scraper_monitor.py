"""
Scraper Health Monitoring System.
Monitors scraper health, detects failures, and provides metrics for auto-correction.
"""
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ScraperStatus(str, Enum):
    """Scraper health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


@dataclass
class ScraperMetrics:
    """Metrics for a single scraper run."""
    scraper_name: str
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    properties_found: int = 0
    properties_valid: int = 0
    properties_invalid: int = 0
    urls_validated: int = 0
    urls_redirected: int = 0
    urls_failed: int = 0
    rate_limit_hits: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        total = self.properties_found
        if total == 0:
            return 0.0
        return (self.properties_valid / total) * 100
    
    @property
    def url_validation_rate(self) -> float:
        total = self.urls_validated
        if total == 0:
            return 0.0
        valid = total - self.urls_failed - self.urls_redirected
        return (valid / total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scraper_name": self.scraper_name,
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "properties_found": self.properties_found,
            "properties_valid": self.properties_valid,
            "properties_invalid": self.properties_invalid,
            "success_rate": round(self.success_rate, 2),
            "urls_validated": self.urls_validated,
            "urls_redirected": self.urls_redirected,
            "urls_failed": self.urls_failed,
            "url_validation_rate": round(self.url_validation_rate, 2),
            "rate_limit_hits": self.rate_limit_hits,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class ScraperHealthReport:
    """Health report for a scraper."""
    scraper_name: str
    status: ScraperStatus
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    avg_success_rate: float = 0.0
    avg_properties_per_run: float = 0.0
    total_runs: int = 0
    total_properties: int = 0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scraper_name": self.scraper_name,
            "status": self.status.value,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "consecutive_failures": self.consecutive_failures,
            "avg_success_rate": round(self.avg_success_rate, 2),
            "avg_properties_per_run": round(self.avg_properties_per_run, 2),
            "total_runs": self.total_runs,
            "total_properties": self.total_properties,
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


class ScraperMonitor:
    """
    Monitors scraper health and provides metrics for auto-correction.
    
    Features:
    - Track scraper run metrics (success rate, properties found, errors)
    - Detect failures and degraded performance
    - Provide health reports with recommendations
    - Store historical metrics for trend analysis
    """
    
    # Thresholds for health status
    SUCCESS_RATE_HEALTHY = 80.0  # Above this = healthy
    SUCCESS_RATE_DEGRADED = 50.0  # Above this = degraded, below = failing
    MAX_CONSECUTIVE_FAILURES = 3  # After this, mark as failing
    METRICS_RETENTION_DAYS = 7  # Keep metrics for this many days
    
    def __init__(self):
        self.metrics_history: Dict[str, List[ScraperMetrics]] = {}
        self.current_runs: Dict[str, ScraperMetrics] = {}
        self._run_counter = 0
    
    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        self._run_counter += 1
        return f"run_{int(time.time())}_{self._run_counter}"
    
    def start_run(self, scraper_name: str) -> str:
        """
        Start tracking a new scraper run.
        
        Args:
            scraper_name: Name of the scraper
            
        Returns:
            Run ID for tracking this run
        """
        run_id = self._generate_run_id()
        metrics = ScraperMetrics(
            scraper_name=scraper_name,
            run_id=run_id,
            start_time=datetime.now(),
        )
        self.current_runs[run_id] = metrics
        logger.info(f"Started monitoring run {run_id} for scraper {scraper_name}")
        return run_id
    
    def end_run(self, run_id: str, success: bool = True) -> Optional[ScraperMetrics]:
        """
        End a scraper run and store metrics.
        
        Args:
            run_id: The run ID from start_run
            success: Whether the run completed successfully
            
        Returns:
            The final metrics for this run
        """
        if run_id not in self.current_runs:
            logger.warning(f"Unknown run ID: {run_id}")
            return None
        
        metrics = self.current_runs.pop(run_id)
        metrics.end_time = datetime.now()
        
        if not success:
            metrics.errors.append("Run marked as failed")
        
        # Store in history
        scraper_name = metrics.scraper_name
        if scraper_name not in self.metrics_history:
            self.metrics_history[scraper_name] = []
        self.metrics_history[scraper_name].append(metrics)
        
        # Clean up old metrics
        self._cleanup_old_metrics(scraper_name)
        
        logger.info(f"Ended run {run_id} for {scraper_name}: "
                   f"{metrics.properties_valid}/{metrics.properties_found} valid properties, "
                   f"success rate: {metrics.success_rate:.1f}%")
        
        return metrics
    
    def record_property_found(self, run_id: str, valid: bool = True) -> None:
        """Record a property found during scraping."""
        if run_id in self.current_runs:
            self.current_runs[run_id].properties_found += 1
            if valid:
                self.current_runs[run_id].properties_valid += 1
            else:
                self.current_runs[run_id].properties_invalid += 1
    
    def record_url_validation(self, run_id: str, status: str) -> None:
        """
        Record URL validation result.
        
        Args:
            run_id: The run ID
            status: 'ok', 'redirected', or 'failed'
        """
        if run_id in self.current_runs:
            self.current_runs[run_id].urls_validated += 1
            if status == 'redirected' or status == 'redirects_to_listing':
                self.current_runs[run_id].urls_redirected += 1
            elif status in ('failed', 'error', 'not_found'):
                self.current_runs[run_id].urls_failed += 1
    
    def record_rate_limit(self, run_id: str) -> None:
        """Record a rate limit hit (429 error)."""
        if run_id in self.current_runs:
            self.current_runs[run_id].rate_limit_hits += 1
    
    def record_error(self, run_id: str, error: str) -> None:
        """Record an error during scraping."""
        if run_id in self.current_runs:
            self.current_runs[run_id].errors.append(error)
            logger.error(f"Run {run_id}: {error}")
    
    def record_warning(self, run_id: str, warning: str) -> None:
        """Record a warning during scraping."""
        if run_id in self.current_runs:
            self.current_runs[run_id].warnings.append(warning)
            logger.warning(f"Run {run_id}: {warning}")
    
    def get_health_report(self, scraper_name: str) -> ScraperHealthReport:
        """
        Generate a health report for a scraper.
        
        Args:
            scraper_name: Name of the scraper
            
        Returns:
            Health report with status, metrics, and recommendations
        """
        history = self.metrics_history.get(scraper_name, [])
        
        report = ScraperHealthReport(
            scraper_name=scraper_name,
            status=ScraperStatus.UNKNOWN,
            total_runs=len(history),
        )
        
        if not history:
            report.issues.append("No run history available")
            report.recommendations.append("Run the scraper to collect baseline metrics")
            return report
        
        # Calculate metrics from history
        recent_runs = history[-10:]  # Last 10 runs
        
        # Last run info
        last_run = history[-1]
        report.last_run = last_run.start_time
        
        # Calculate averages
        total_success_rate = sum(r.success_rate for r in recent_runs)
        report.avg_success_rate = total_success_rate / len(recent_runs)
        
        total_properties = sum(r.properties_valid for r in recent_runs)
        report.avg_properties_per_run = total_properties / len(recent_runs)
        report.total_properties = sum(r.properties_valid for r in history)
        
        # Count consecutive failures
        consecutive_failures = 0
        for run in reversed(history):
            if run.success_rate < self.SUCCESS_RATE_DEGRADED or run.errors:
                consecutive_failures += 1
            else:
                break
        report.consecutive_failures = consecutive_failures
        
        # Find last successful run
        for run in reversed(history):
            if run.success_rate >= self.SUCCESS_RATE_HEALTHY and not run.errors:
                report.last_success = run.start_time
                break
        
        # Determine status
        if consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            report.status = ScraperStatus.FAILING
        elif report.avg_success_rate >= self.SUCCESS_RATE_HEALTHY:
            report.status = ScraperStatus.HEALTHY
        elif report.avg_success_rate >= self.SUCCESS_RATE_DEGRADED:
            report.status = ScraperStatus.DEGRADED
        else:
            report.status = ScraperStatus.FAILING
        
        # Identify issues and recommendations
        self._analyze_issues(report, recent_runs)
        
        return report
    
    def _analyze_issues(self, report: ScraperHealthReport, recent_runs: List[ScraperMetrics]) -> None:
        """Analyze recent runs and add issues/recommendations to report."""
        
        # Check for rate limiting issues
        total_rate_limits = sum(r.rate_limit_hits for r in recent_runs)
        if total_rate_limits > 5:
            report.issues.append(f"High rate limiting: {total_rate_limits} hits in recent runs")
            report.recommendations.append("Increase delay between requests or implement better backoff")
        
        # Check for URL validation issues
        total_redirects = sum(r.urls_redirected for r in recent_runs)
        total_validated = sum(r.urls_validated for r in recent_runs)
        if total_validated > 0:
            redirect_rate = (total_redirects / total_validated) * 100
            if redirect_rate > 20:
                report.issues.append(f"High URL redirect rate: {redirect_rate:.1f}%")
                report.recommendations.append("Check if website structure has changed")
        
        # Check for declining performance
        if len(recent_runs) >= 3:
            first_half = recent_runs[:len(recent_runs)//2]
            second_half = recent_runs[len(recent_runs)//2:]
            
            first_avg = sum(r.properties_valid for r in first_half) / len(first_half)
            second_avg = sum(r.properties_valid for r in second_half) / len(second_half)
            
            if second_avg < first_avg * 0.5:
                report.issues.append("Significant decline in properties found")
                report.recommendations.append("Website may have changed structure - review scraper selectors")
        
        # Check for errors
        recent_errors = []
        for run in recent_runs:
            recent_errors.extend(run.errors)
        
        if recent_errors:
            unique_errors = list(set(recent_errors))[:5]  # Top 5 unique errors
            for error in unique_errors:
                report.issues.append(f"Error: {error[:100]}")
        
        # Check for low property count
        if report.avg_properties_per_run < 5:
            report.issues.append("Very low property count per run")
            report.recommendations.append("Check if scraper is finding property elements correctly")
        
        # Status-specific recommendations
        if report.status == ScraperStatus.FAILING:
            report.recommendations.append("Scraper needs immediate attention - check website accessibility")
            report.recommendations.append("Review scraper logs for detailed error information")
        elif report.status == ScraperStatus.DEGRADED:
            report.recommendations.append("Monitor scraper closely - performance is below optimal")
    
    def _cleanup_old_metrics(self, scraper_name: str) -> None:
        """Remove metrics older than retention period."""
        if scraper_name not in self.metrics_history:
            return
        
        cutoff = datetime.now() - timedelta(days=self.METRICS_RETENTION_DAYS)
        self.metrics_history[scraper_name] = [
            m for m in self.metrics_history[scraper_name]
            if m.start_time > cutoff
        ]
    
    def get_all_health_reports(self) -> List[ScraperHealthReport]:
        """Get health reports for all tracked scrapers."""
        reports = []
        for scraper_name in self.metrics_history.keys():
            reports.append(self.get_health_report(scraper_name))
        return reports
    
    def get_metrics_history(self, scraper_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent metrics history for a scraper."""
        history = self.metrics_history.get(scraper_name, [])
        return [m.to_dict() for m in history[-limit:]]
    
    def check_scraper_health(self, scraper_name: str, base_url: str) -> Dict[str, Any]:
        """
        Perform a quick health check on a scraper's target website.
        
        Args:
            scraper_name: Name of the scraper
            base_url: Base URL of the website to check
            
        Returns:
            Health check result with status and details
        """
        result = {
            "scraper_name": scraper_name,
            "base_url": base_url,
            "timestamp": datetime.now().isoformat(),
            "accessible": False,
            "response_time_ms": None,
            "status_code": None,
            "error": None,
        }
        
        try:
            start_time = time.time()
            response = requests.get(
                base_url,
                timeout=10,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response_time = (time.time() - start_time) * 1000
            
            result["accessible"] = response.status_code == 200
            result["response_time_ms"] = round(response_time, 2)
            result["status_code"] = response.status_code
            
            if response.status_code == 429:
                result["error"] = "Rate limited - too many requests"
            elif response.status_code == 403:
                result["error"] = "Access forbidden - may be blocked"
            elif response.status_code >= 500:
                result["error"] = "Server error - website may be down"
            elif response.status_code != 200:
                result["error"] = f"Unexpected status code: {response.status_code}"
                
        except requests.exceptions.Timeout:
            result["error"] = "Request timed out"
        except requests.exceptions.ConnectionError:
            result["error"] = "Connection failed - website may be down"
        except Exception as e:
            result["error"] = str(e)
        
        return result


# Global monitor instance
scraper_monitor = ScraperMonitor()


def get_scraper_monitor() -> ScraperMonitor:
    """Get the global scraper monitor instance."""
    return scraper_monitor
