"""
Autonomous Scheduler Service.
Handles automatic scraping, 80/20 analysis, white-label detection, and periodic data refresh.
"""
import logging
import json
import os
import time
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from threading import Thread
from bs4 import BeautifulSoup

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class AuctioneerPriority(str, Enum):
    """Priority level for auctioneer scraping frequency."""
    HIGH = "high"      # Top 20% by volume - daily
    MEDIUM = "medium"  # Middle 30% - every 2-3 days
    LOW = "low"        # Bottom 50% - weekly
    UNKNOWN = "unknown"


class PlatformType(str, Enum):
    """Known white-label platform types."""
    LEILOES_WEB = "leiloes_web"
    SUPERBID = "superbid"
    MEGA_PLATFORM = "mega_platform"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass
class AuctioneerInfo:
    """Information about an auctioneer for the catalog."""
    id: str
    name: str
    url: str
    approx_property_count: int = 0
    platform_type: PlatformType = PlatformType.UNKNOWN
    platform_signatures: List[str] = field(default_factory=list)
    priority: AuctioneerPriority = AuctioneerPriority.UNKNOWN
    has_captcha: bool = False
    last_scanned: Optional[str] = None
    last_scraped: Optional[str] = None
    scraper_implemented: bool = False
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "approx_property_count": self.approx_property_count,
            "platform_type": self.platform_type.value if isinstance(self.platform_type, PlatformType) else self.platform_type,
            "platform_signatures": self.platform_signatures,
            "priority": self.priority.value if isinstance(self.priority, AuctioneerPriority) else self.priority,
            "has_captcha": self.has_captcha,
            "last_scanned": self.last_scanned,
            "last_scraped": self.last_scraped,
            "scraper_implemented": self.scraper_implemented,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuctioneerInfo":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            url=data.get("url", ""),
            approx_property_count=data.get("approx_property_count", 0),
            platform_type=PlatformType(data.get("platform_type", "unknown")),
            platform_signatures=data.get("platform_signatures", []),
            priority=AuctioneerPriority(data.get("priority", "unknown")),
            has_captcha=data.get("has_captcha", False),
            last_scanned=data.get("last_scanned"),
            last_scraped=data.get("last_scraped"),
            scraper_implemented=data.get("scraper_implemented", False),
            notes=data.get("notes", ""),
        )


@dataclass
class ScraperJobStatus:
    """Status of a background scraper job."""
    job_id: str
    scraper_name: str
    status: str  # "pending", "running", "completed", "failed"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    properties_scraped: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchedulerStatus:
    """Status of the autonomous scheduler."""
    is_running: bool = False
    started_at: Optional[str] = None
    total_auctioneers_cataloged: int = 0
    auctioneers_with_scrapers: int = 0
    last_80_20_scan: Optional[str] = None
    next_80_20_scan: Optional[str] = None
    jobs_scheduled: int = 0
    jobs_completed_today: int = 0
    jobs_failed_today: int = 0
    background_job_running: bool = False
    current_scraper: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutonomousScheduler:
    """
    Autonomous scheduler that handles:
    1. 80/20 analysis - scanning auctioneers to rank by property count
    2. White-label detection - identifying platform families
    3. Periodic data refresh - running scrapers on schedule
    4. Background job execution - running scrapers without HTTP timeout
    """
    
    CATALOG_FILE = "/tmp/auctioneer_catalog.json"
    STATUS_FILE = "/tmp/scheduler_status.json"
    JOBS_FILE = "/tmp/scraper_jobs.json"
    
    # Platform detection signatures
    PLATFORM_SIGNATURES = {
        PlatformType.LEILOES_WEB: [
            "Leilões Web",
            "leiloesweb.com.br",
            "Leilões online, presenciais e simultâneos",
        ],
        PlatformType.SUPERBID: [
            "superbid",
            "sbwebservices.net",
        ],
        PlatformType.MEGA_PLATFORM: [
            "megaleiloes.com.br",
            "cdn1.megaleiloes.com.br",
        ],
    }
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.catalog: Dict[str, AuctioneerInfo] = {}
        self.status = SchedulerStatus()
        self._load_catalog()
        self._load_status()
        
    def _load_catalog(self) -> None:
        """Load auctioneer catalog from file."""
        if os.path.exists(self.CATALOG_FILE):
            try:
                with open(self.CATALOG_FILE, 'r') as f:
                    data = json.load(f)
                    self.catalog = {
                        k: AuctioneerInfo.from_dict(v) 
                        for k, v in data.items()
                    }
                logger.info(f"Loaded {len(self.catalog)} auctioneers from catalog")
            except Exception as e:
                logger.error(f"Error loading catalog: {e}")
                self.catalog = {}
        
    def _save_catalog(self) -> None:
        """Save auctioneer catalog to file."""
        try:
            with open(self.CATALOG_FILE, 'w') as f:
                json.dump(
                    {k: v.to_dict() for k, v in self.catalog.items()},
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            logger.info(f"Saved {len(self.catalog)} auctioneers to catalog")
        except Exception as e:
            logger.error(f"Error saving catalog: {e}")
    
    def _load_status(self) -> None:
        """Load scheduler status from file."""
        if os.path.exists(self.STATUS_FILE):
            try:
                with open(self.STATUS_FILE, 'r') as f:
                    data = json.load(f)
                    self.status = SchedulerStatus(**data)
            except Exception as e:
                logger.error(f"Error loading status: {e}")
                self.status = SchedulerStatus()
    
    def _save_status(self) -> None:
        """Save scheduler status to file."""
        try:
            with open(self.STATUS_FILE, 'w') as f:
                json.dump(self.status.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving status: {e}")
    
    def start(self) -> None:
        """Start the autonomous scheduler."""
        if self.status.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting autonomous scheduler...")
        
        # Schedule the 80/20 analysis job (runs once on startup, then weekly)
        self.scheduler.add_job(
            self._run_80_20_analysis,
            CronTrigger(day_of_week='sun', hour=2),  # Weekly on Sunday at 2 AM
            id='80_20_analysis',
            name='80/20 Auctioneer Analysis',
            replace_existing=True,
        )
        
        # Schedule periodic scraper runs based on priority
        self.scheduler.add_job(
            self._run_high_priority_scrapers,
            CronTrigger(hour='*/6'),  # Every 6 hours
            id='high_priority_scrapers',
            name='High Priority Scrapers (Top 20%)',
            replace_existing=True,
        )
        
        self.scheduler.add_job(
            self._run_medium_priority_scrapers,
            CronTrigger(hour=3, day_of_week='mon,wed,fri'),  # Mon, Wed, Fri at 3 AM
            id='medium_priority_scrapers',
            name='Medium Priority Scrapers',
            replace_existing=True,
        )
        
        self.scheduler.add_job(
            self._run_low_priority_scrapers,
            CronTrigger(hour=4, day_of_week='sat'),  # Saturday at 4 AM
            id='low_priority_scrapers',
            name='Low Priority Scrapers',
            replace_existing=True,
        )
        
        # Start the scheduler
        self.scheduler.start()
        
        self.status.is_running = True
        self.status.started_at = datetime.now().isoformat()
        self.status.jobs_scheduled = len(self.scheduler.get_jobs())
        self._save_status()
        
        logger.info(f"Autonomous scheduler started with {self.status.jobs_scheduled} jobs")
        
        # Note: We don't run the 80/20 analysis immediately on startup
        # to avoid causing issues with the machine startup.
        # The analysis will run on the scheduled time (Sunday at 2 AM)
        # or can be triggered manually via the API endpoint.
        if not self.catalog:
            logger.info("Catalog is empty. Use POST /api/scheduler/analyze-80-20 to trigger analysis.")
    
    def stop(self) -> None:
        """Stop the autonomous scheduler."""
        if not self.status.is_running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping autonomous scheduler...")
        self.scheduler.shutdown(wait=False)
        self.status.is_running = False
        self._save_status()
        logger.info("Autonomous scheduler stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        self.status.total_auctioneers_cataloged = len(self.catalog)
        self.status.auctioneers_with_scrapers = sum(
            1 for a in self.catalog.values() if a.scraper_implemented
        )
        
        # Get next run times
        jobs = self.scheduler.get_jobs() if self.status.is_running else []
        next_runs = {}
        for job in jobs:
            if job.next_run_time:
                next_runs[job.id] = job.next_run_time.isoformat()
        
        return {
            **self.status.to_dict(),
            "next_scheduled_runs": next_runs,
            "platform_distribution": self._get_platform_distribution(),
            "priority_distribution": self._get_priority_distribution(),
        }
    
    def _get_platform_distribution(self) -> Dict[str, int]:
        """Get distribution of auctioneers by platform type."""
        distribution = {}
        for auctioneer in self.catalog.values():
            platform = auctioneer.platform_type.value if isinstance(auctioneer.platform_type, PlatformType) else auctioneer.platform_type
            distribution[platform] = distribution.get(platform, 0) + 1
        return distribution
    
    def _get_priority_distribution(self) -> Dict[str, int]:
        """Get distribution of auctioneers by priority."""
        distribution = {}
        for auctioneer in self.catalog.values():
            priority = auctioneer.priority.value if isinstance(auctioneer.priority, AuctioneerPriority) else auctioneer.priority
            distribution[priority] = distribution.get(priority, 0) + 1
        return distribution
    
    def _run_80_20_analysis(self) -> Dict[str, Any]:
        """
        Run the 80/20 analysis:
        1. Fetch list of auctioneers from source
        2. Probe each auctioneer to count properties
        3. Detect platform type
        4. Rank by property count
        5. Assign priorities
        """
        logger.info("Starting 80/20 analysis...")
        start_time = datetime.now()
        results = {
            "started_at": start_time.isoformat(),
            "auctioneers_scanned": 0,
            "auctioneers_with_properties": 0,
            "total_properties_found": 0,
            "platforms_detected": {},
            "errors": [],
        }
        
        try:
            # For now, use our known auctioneers as a starting point
            # In production, this would fetch from renatoparanhosleilao.com.br
            known_auctioneers = self._get_known_auctioneers()
            
            for auctioneer_data in known_auctioneers:
                try:
                    auctioneer_id = auctioneer_data["id"]
                    
                    # Skip if recently scanned (within 24 hours)
                    if auctioneer_id in self.catalog:
                        existing = self.catalog[auctioneer_id]
                        if existing.last_scanned:
                            last_scan = datetime.fromisoformat(existing.last_scanned)
                            if datetime.now() - last_scan < timedelta(hours=24):
                                continue
                    
                    # Probe the auctioneer website
                    probe_result = self._probe_auctioneer(
                        auctioneer_data["url"],
                        auctioneer_data["name"]
                    )
                    
                    # Create or update catalog entry
                    auctioneer = AuctioneerInfo(
                        id=auctioneer_id,
                        name=auctioneer_data["name"],
                        url=auctioneer_data["url"],
                        approx_property_count=probe_result.get("property_count", 0),
                        platform_type=probe_result.get("platform_type", PlatformType.UNKNOWN),
                        platform_signatures=probe_result.get("signatures", []),
                        has_captcha=probe_result.get("has_captcha", False),
                        last_scanned=datetime.now().isoformat(),
                        scraper_implemented=auctioneer_data.get("scraper_implemented", False),
                    )
                    
                    self.catalog[auctioneer_id] = auctioneer
                    results["auctioneers_scanned"] += 1
                    
                    if auctioneer.approx_property_count > 0:
                        results["auctioneers_with_properties"] += 1
                        results["total_properties_found"] += auctioneer.approx_property_count
                    
                    # Track platform distribution
                    platform = auctioneer.platform_type.value
                    results["platforms_detected"][platform] = results["platforms_detected"].get(platform, 0) + 1
                    
                    # Small delay to be polite
                    time.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Error scanning {auctioneer_data.get('name', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Assign priorities based on 80/20 rule
            self._assign_priorities()
            
            # Save catalog
            self._save_catalog()
            
            # Update status
            self.status.last_80_20_scan = datetime.now().isoformat()
            self._save_status()
            
            results["completed_at"] = datetime.now().isoformat()
            results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"80/20 analysis completed: {results['auctioneers_scanned']} scanned, "
                       f"{results['total_properties_found']} properties found")
            
        except Exception as e:
            logger.error(f"Error in 80/20 analysis: {e}")
            results["errors"].append(str(e))
        
        return results
    
    def _get_known_auctioneers(self) -> List[Dict[str, Any]]:
        """Get list of known auctioneers to scan."""
        # These are the auctioneers we know about
        # In production, this would be fetched from renatoparanhosleilao.com.br
        return [
            {"id": "portal_zuk", "name": "Portal Zuk", "url": "https://www.portalzuk.com.br", "scraper_implemented": True},
            {"id": "superbid", "name": "Superbid", "url": "https://www.superbid.net", "scraper_implemented": True},
            {"id": "megaleiloes", "name": "Mega Leilões", "url": "https://www.megaleiloes.com.br", "scraper_implemented": True},
            {"id": "leilaovip", "name": "Leilão VIP", "url": "https://www.leilaovip.com.br", "scraper_implemented": True},
            {"id": "inovaleilao", "name": "Inova Leilão", "url": "https://www.inovaleilao.com.br", "scraper_implemented": True},
            {"id": "pestana", "name": "Pestana Leilões", "url": "https://www.pestanaleiloes.com.br", "scraper_implemented": True},
            {"id": "silas", "name": "Silas Leiloeiro", "url": "https://silasleiloeiro.lel.br", "scraper_implemented": True},
            {"id": "roberto_fernandes", "name": "Roberto Fernandes Leilões", "url": "https://www.robertofernandesleiloes.com.br", "scraper_implemented": True},
            {"id": "mauricio_mariz", "name": "Mauricio Mariz Leilões", "url": "https://www.mauriciomarizleiloes.com.br", "scraper_implemented": True},
            # Additional auctioneers to scan (not yet implemented)
            {"id": "freitas", "name": "Freitas Leiloeiro", "url": "https://www.freitasleiloeiro.com.br", "scraper_implemented": False},
            {"id": "caixa", "name": "Caixa Leilões", "url": "https://www.caixa.gov.br/voce/habitacao/imoveis-venda/Paginas/default.aspx", "scraper_implemented": False},
            {"id": "bomvalor", "name": "Bom Valor", "url": "https://www.bomvalor.com.br", "scraper_implemented": False},
            {"id": "mpleilao", "name": "MP Leilão", "url": "https://www.mpleilao.com.br", "scraper_implemented": False},
            {"id": "sodre_santoro", "name": "Sodré Santoro", "url": "https://www.sodresantoro.com.br", "scraper_implemented": False},
            {"id": "biasi", "name": "Biasi Leilões", "url": "https://www.biasileiloes.com.br", "scraper_implemented": False},
            {"id": "frazao", "name": "Frazão Leilões", "url": "https://www.frazaoleiloes.com.br", "scraper_implemented": False},
            {"id": "lut", "name": "LUT Leilões", "url": "https://www.lfrancaleiloes.com.br", "scraper_implemented": False},
            {"id": "vip_leiloes", "name": "VIP Leilões", "url": "https://www.vipleiloes.com.br", "scraper_implemented": False},
            {"id": "zukerman", "name": "Zukerman Leilões", "url": "https://www.zfrancaleiloes.com.br", "scraper_implemented": False},
        ]
    
    def _probe_auctioneer(self, url: str, name: str) -> Dict[str, Any]:
        """
        Probe an auctioneer website to:
        1. Count approximate properties
        2. Detect platform type
        3. Check for captcha
        """
        result = {
            "property_count": 0,
            "platform_type": PlatformType.UNKNOWN,
            "signatures": [],
            "has_captcha": False,
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            # Check for Cloudflare/captcha
            if response.status_code == 403 or 'cf-browser-verification' in response.text.lower():
                result["has_captcha"] = True
                logger.warning(f"{name}: Cloudflare/captcha detected")
                return result
            
            if response.status_code != 200:
                logger.warning(f"{name}: HTTP {response.status_code}")
                return result
            
            soup = BeautifulSoup(response.text, 'lxml')
            html_text = response.text.lower()
            
            # Detect platform type
            for platform, signatures in self.PLATFORM_SIGNATURES.items():
                for sig in signatures:
                    if sig.lower() in html_text:
                        result["platform_type"] = platform
                        result["signatures"].append(sig)
                        break
                if result["platform_type"] != PlatformType.UNKNOWN:
                    break
            
            # Try to count properties (heuristic)
            # Look for common patterns in auction listing pages
            property_count = 0
            
            # Method 1: Look for lot/property cards
            lot_selectors = [
                'div[class*="lot"]',
                'div[class*="property"]',
                'div[class*="imovel"]',
                'div[class*="card"]',
                'article[class*="lot"]',
                'li[class*="lot"]',
            ]
            
            for selector in lot_selectors:
                elements = soup.select(selector)
                if len(elements) > property_count:
                    property_count = len(elements)
            
            # Method 2: Look for "X imóveis" or "X lotes" text
            import re
            count_patterns = [
                r'(\d+)\s*im[óo]ve?is?',
                r'(\d+)\s*lotes?',
                r'(\d+)\s*resultados?',
                r'total[:\s]+(\d+)',
            ]
            
            for pattern in count_patterns:
                matches = re.findall(pattern, html_text)
                for match in matches:
                    try:
                        count = int(match)
                        if count > property_count and count < 10000:  # Sanity check
                            property_count = count
                    except ValueError:
                        pass
            
            result["property_count"] = property_count
            
            logger.info(f"{name}: {property_count} properties, platform: {result['platform_type'].value}")
            
        except requests.exceptions.Timeout:
            logger.warning(f"{name}: Request timeout")
        except requests.exceptions.ConnectionError:
            logger.warning(f"{name}: Connection error")
        except Exception as e:
            logger.error(f"{name}: Error probing - {e}")
        
        return result
    
    def _assign_priorities(self) -> None:
        """Assign priorities based on 80/20 rule."""
        if not self.catalog:
            return
        
        # Sort by property count descending
        sorted_auctioneers = sorted(
            self.catalog.values(),
            key=lambda x: x.approx_property_count,
            reverse=True
        )
        
        total = len(sorted_auctioneers)
        top_20_cutoff = int(total * 0.2)
        top_50_cutoff = int(total * 0.5)
        
        for i, auctioneer in enumerate(sorted_auctioneers):
            if i < top_20_cutoff:
                auctioneer.priority = AuctioneerPriority.HIGH
            elif i < top_50_cutoff:
                auctioneer.priority = AuctioneerPriority.MEDIUM
            else:
                auctioneer.priority = AuctioneerPriority.LOW
        
        logger.info(f"Assigned priorities: {top_20_cutoff} HIGH, "
                   f"{top_50_cutoff - top_20_cutoff} MEDIUM, "
                   f"{total - top_50_cutoff} LOW")
    
    def _run_high_priority_scrapers(self) -> None:
        """Run scrapers for high priority auctioneers."""
        logger.info("Running high priority scrapers...")
        self._run_scrapers_by_priority(AuctioneerPriority.HIGH)
    
    def _run_medium_priority_scrapers(self) -> None:
        """Run scrapers for medium priority auctioneers."""
        logger.info("Running medium priority scrapers...")
        self._run_scrapers_by_priority(AuctioneerPriority.MEDIUM)
    
    def _run_low_priority_scrapers(self) -> None:
        """Run scrapers for low priority auctioneers."""
        logger.info("Running low priority scrapers...")
        self._run_scrapers_by_priority(AuctioneerPriority.LOW)
    
    def _run_scrapers_by_priority(self, priority: AuctioneerPriority) -> None:
        """Run all scrapers with the given priority."""
        auctioneers = [
            a for a in self.catalog.values()
            if a.priority == priority and a.scraper_implemented and not a.has_captcha
        ]
        
        logger.info(f"Found {len(auctioneers)} {priority.value} priority auctioneers to scrape")
        
        for auctioneer in auctioneers:
            try:
                # In production, this would call the actual scraper
                # For now, we just log and update the timestamp
                logger.info(f"Would scrape: {auctioneer.name}")
                auctioneer.last_scraped = datetime.now().isoformat()
                self.status.jobs_completed_today += 1
            except Exception as e:
                logger.error(f"Error scraping {auctioneer.name}: {e}")
                self.status.jobs_failed_today += 1
        
        self._save_catalog()
        self._save_status()
    
    def get_catalog(self) -> List[Dict[str, Any]]:
        """Get the full auctioneer catalog."""
        return [a.to_dict() for a in sorted(
            self.catalog.values(),
            key=lambda x: x.approx_property_count,
            reverse=True
        )]
    
    def get_80_20_ranking(self) -> Dict[str, Any]:
        """Get the 80/20 ranking of auctioneers."""
        sorted_auctioneers = sorted(
            self.catalog.values(),
            key=lambda x: x.approx_property_count,
            reverse=True
        )
        
        total_properties = sum(a.approx_property_count for a in sorted_auctioneers)
        
        # Calculate cumulative percentage
        ranking = []
        cumulative = 0
        for i, auctioneer in enumerate(sorted_auctioneers):
            cumulative += auctioneer.approx_property_count
            percentage = (cumulative / total_properties * 100) if total_properties > 0 else 0
            ranking.append({
                "rank": i + 1,
                "name": auctioneer.name,
                "url": auctioneer.url,
                "property_count": auctioneer.approx_property_count,
                "cumulative_percentage": round(percentage, 2),
                "priority": auctioneer.priority.value,
                "platform_type": auctioneer.platform_type.value,
                "scraper_implemented": auctioneer.scraper_implemented,
            })
        
        return {
            "total_auctioneers": len(ranking),
            "total_properties": total_properties,
            "ranking": ranking,
            "top_20_percent_count": len([r for r in ranking if r["cumulative_percentage"] <= 80]),
        }
    
    def get_platform_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get auctioneers grouped by platform type."""
        groups = {}
        for auctioneer in self.catalog.values():
            platform = auctioneer.platform_type.value
            if platform not in groups:
                groups[platform] = []
            groups[platform].append({
                "name": auctioneer.name,
                "url": auctioneer.url,
                "property_count": auctioneer.approx_property_count,
                "scraper_implemented": auctioneer.scraper_implemented,
            })
        
        # Sort each group by property count
        for platform in groups:
            groups[platform] = sorted(
                groups[platform],
                key=lambda x: x["property_count"],
                reverse=True
            )
        
        return groups
    
    def trigger_80_20_analysis(self) -> Dict[str, Any]:
        """Manually trigger the 80/20 analysis."""
        logger.info("Manually triggering 80/20 analysis...")
        return self._run_80_20_analysis()
    
    def add_auctioneer(self, id: str, name: str, url: str) -> AuctioneerInfo:
        """Add a new auctioneer to the catalog."""
        auctioneer = AuctioneerInfo(
            id=id,
            name=name,
            url=url,
        )
        self.catalog[id] = auctioneer
        self._save_catalog()
        return auctioneer
    
    # ==================== Background Job System ====================
    
    def _load_jobs(self) -> Dict[str, ScraperJobStatus]:
        """Load scraper jobs from file."""
        if os.path.exists(self.JOBS_FILE):
            try:
                with open(self.JOBS_FILE, 'r') as f:
                    data = json.load(f)
                    return {k: ScraperJobStatus(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading jobs: {e}")
        return {}
    
    def _save_jobs(self, jobs: Dict[str, ScraperJobStatus]) -> None:
        """Save scraper jobs to file."""
        try:
            with open(self.JOBS_FILE, 'w') as f:
                json.dump({k: v.to_dict() for k, v in jobs.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")
    
    def start_background_scraping(self, max_per_scraper: Optional[int] = None) -> Dict[str, Any]:
        """
        Start background scraping job that runs all integrated scrapers sequentially.
        Returns immediately with job ID - scraping happens in background thread.
        
        Args:
            max_per_scraper: Maximum properties per scraper. None = no limit (collect ALL)
        """
        import uuid
        import gc
        
        if self.status.background_job_running:
            return {
                "success": False,
                "error": "A background job is already running",
                "current_scraper": self.status.current_scraper,
            }
        
        job_id = str(uuid.uuid4())[:8]
        
        # Create job status entries
        jobs = self._load_jobs()
        scrapers_to_run = [
            "Portal Zuk", "Superbid", "Mega Leilões", 
            "Leilão VIP", "Inova Leilão", "Pestana Leilões"
        ]
        
        for scraper_name in scrapers_to_run:
            jobs[f"{job_id}_{scraper_name}"] = ScraperJobStatus(
                job_id=job_id,
                scraper_name=scraper_name,
                status="pending",
            )
        self._save_jobs(jobs)
        
        # Start background thread
        def run_scrapers_background():
            import gc
            from app.services import db
            
            self.status.background_job_running = True
            self._save_status()
            
            scraper_configs = [
                {"name": "Portal Zuk", "module": "app.scrapers.portalzuk_scraper_v2", "class": "PortalZukScraperV2", "method": "scrape_properties"},
                {"name": "Superbid", "module": "app.scrapers.superbid_scraper", "class": "SuperbidScraper", "method": "scrape_properties"},
                {"name": "Mega Leilões", "module": "app.scrapers.megaleiloes_scraper", "class": "MegaleiloesScraper", "method": "scrape_properties"},
                {"name": "Leilão VIP", "module": "app.scrapers.leilaovip_scraper", "class": "LeilaoVipScraper", "method": "scrape_properties"},
                {"name": "Inova Leilão", "module": "app.scrapers.inovaleilao_scraper", "class": "InovaLeilaoScraper", "method": "scrape_properties"},
                {"name": "Pestana Leilões", "module": "app.scrapers.pestana_scraper", "class": "PestanaScraper", "method": "scrape_properties"},
            ]
            
            for config in scraper_configs:
                job_key = f"{job_id}_{config['name']}"
                jobs = self._load_jobs()
                
                try:
                    # Update status to running
                    self.status.current_scraper = config['name']
                    self._save_status()
                    
                    jobs[job_key].status = "running"
                    jobs[job_key].started_at = datetime.now().isoformat()
                    self._save_jobs(jobs)
                    
                    logger.info(f"Background job: Starting {config['name']}")
                    
                    # Import and run scraper
                    import importlib
                    module = importlib.import_module(config['module'])
                    scraper_class = getattr(module, config['class'])
                    scraper = scraper_class()
                    method = getattr(scraper, config['method'])
                    # Pass max_properties only if a limit is set, otherwise scrape ALL
                    if max_per_scraper is not None:
                        result = method(max_properties=max_per_scraper)
                    else:
                        result = method(max_properties=10000)  # Effectively unlimited
                    
                    # Handle different return types
                    if hasattr(result, 'complete_properties'):
                        properties = result.complete_properties
                    elif isinstance(result, list):
                        properties = result
                    else:
                        properties = []
                    
                    # Add properties to database
                    for prop in properties:
                        # Properties from scrapers are already Property objects
                        # Add them directly to the database dict
                        if hasattr(prop, 'id'):
                            db.properties[prop.id] = prop
                        else:
                            # If it's a dict or PropertyCreate, use create_property
                            from app.models.property import PropertyCreate
                            if isinstance(prop, dict):
                                prop_create = PropertyCreate(**prop)
                                db.create_property(prop_create)
                            else:
                                db.properties[str(uuid.uuid4())] = prop
                    
                    # Update job status
                    jobs = self._load_jobs()
                    jobs[job_key].status = "completed"
                    jobs[job_key].completed_at = datetime.now().isoformat()
                    jobs[job_key].properties_scraped = len(properties)
                    self._save_jobs(jobs)
                    
                    logger.info(f"Background job: Completed {config['name']} - {len(properties)} properties")
                    self.status.jobs_completed_today += 1
                    
                    # Save data to disk after each scraper completes
                    db.save_to_disk()
                    logger.info(f"Background job: Saved data to disk after {config['name']}")
                    
                    # Clean up memory
                    del scraper
                    del result
                    del properties
                    gc.collect()
                    
                except Exception as e:
                    logger.error(f"Background job: Error in {config['name']}: {str(e)}")
                    jobs = self._load_jobs()
                    jobs[job_key].status = "failed"
                    jobs[job_key].completed_at = datetime.now().isoformat()
                    jobs[job_key].error = str(e)
                    self._save_jobs(jobs)
                    self.status.jobs_failed_today += 1
                
                # Small delay between scrapers
                time.sleep(2)
            
            # Mark background job as complete
            self.status.background_job_running = False
            self.status.current_scraper = None
            self._save_status()
            logger.info(f"Background job {job_id} completed")
        
        # Start the background thread
        thread = Thread(target=run_scrapers_background, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Background scraping started. Use GET /api/scheduler/job-status/{job_id} to check progress.",
            "scrapers": scrapers_to_run,
            "max_per_scraper": max_per_scraper if max_per_scraper is not None else "unlimited",
        }
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a background scraping job."""
        jobs = self._load_jobs()
        
        # Filter jobs by job_id
        job_statuses = [
            v.to_dict() for k, v in jobs.items() 
            if v.job_id == job_id
        ]
        
        if not job_statuses:
            return {"error": f"Job {job_id} not found"}
        
        total_properties = sum(j.get("properties_scraped", 0) for j in job_statuses)
        completed = sum(1 for j in job_statuses if j["status"] == "completed")
        failed = sum(1 for j in job_statuses if j["status"] == "failed")
        running = sum(1 for j in job_statuses if j["status"] == "running")
        pending = sum(1 for j in job_statuses if j["status"] == "pending")
        
        overall_status = "running" if running > 0 or pending > 0 else "completed"
        if failed > 0 and completed == 0:
            overall_status = "failed"
        elif failed > 0:
            overall_status = "completed_with_errors"
        
        return {
            "job_id": job_id,
            "overall_status": overall_status,
            "total_scrapers": len(job_statuses),
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "total_properties_scraped": total_properties,
            "scrapers": job_statuses,
        }
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all background job statuses."""
        jobs = self._load_jobs()
        
        # Group by job_id
        job_ids = set(v.job_id for v in jobs.values())
        return [self.get_job_status(job_id) for job_id in job_ids]
    
    def reset_background_job(self) -> Dict[str, Any]:
        """
        Reset background job status. Use this to clear stale jobs after VM restart.
        """
        was_running = self.status.background_job_running
        self.status.background_job_running = False
        self.status.current_scraper = None
        self._save_status()
        
        return {
            "success": True,
            "message": "Background job status reset",
            "was_running": was_running,
        }


# Global scheduler instance
autonomous_scheduler = AutonomousScheduler()


def get_autonomous_scheduler() -> AutonomousScheduler:
    """Get the global autonomous scheduler instance."""
    return autonomous_scheduler
