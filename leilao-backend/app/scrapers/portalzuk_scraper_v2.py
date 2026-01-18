"""
Portal Zuk Scraper V2 - Uses Playwright with stealth.
Based on the approach used in pestana_scraper.py.
"""
import asyncio
import re
import logging
import unicodedata
from typing import List, Dict, Optional, Tuple
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
except ImportError:  # pragma: no cover - optional dependency
    async_playwright = None
    Browser = None
    Page = None
    BrowserContext = None

logger = logging.getLogger(__name__)


class PortalZukScraperV2:
    """Scraper for Portal Zuk using Playwright with stealth configuration."""

    BASE_URL = "https://www.portalzuk.com.br"
    LISTING_URL = f"{BASE_URL}/leilao-de-imoveis"
    AUCTIONEER_ID = "portal_zuk"
    AUCTIONEER_NAME = "Portal Zuk"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.properties: List[Dict] = []

    def scrape_properties(self, max_properties: Optional[int] = None) -> List[Dict]:
        """Synchronous entrypoint for compatibility with the scraper system."""
        return asyncio.run(self._scrape_async(max_properties))

    async def _setup_browser(self) -> None:
        """Configure Playwright browser with stealth settings."""
        if async_playwright is None:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1920,1080",
            ],
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )

        # Basic stealth overrides
        await self.context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
            """
        )

        self.page = await self.context.new_page()

    async def _close_browser(self) -> None:
        """Close Playwright browser."""
        if self.browser:
            await self.browser.close()

    async def _scrape_async(self, max_properties: Optional[int] = None) -> List[Dict]:
        """Async implementation of the scraping flow."""
        try:
            await self._setup_browser()
            logger.info("Starting Portal Zuk scraping")

            await self.page.goto(self.LISTING_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            page_content = await self.page.content()
            if len(page_content) < 1000:
                logger.error("Listing page did not load correctly")
                return []

            property_links = await self._collect_property_links(max_properties)
            logger.info("Found %s property links", len(property_links))

            for idx, url in enumerate(property_links):
                if max_properties and idx >= max_properties:
                    break

                logger.info("Extracting property %s/%s: %s", idx + 1, len(property_links), url)
                property_data = await self._extract_property(url)

                if property_data and property_data.get("title"):
                    self.properties.append(property_data)
                else:
                    logger.warning("Incomplete property data for %s", url)

                await asyncio.sleep(2)

            logger.info("Scraping completed with %s properties", len(self.properties))
            return self.properties

        except Exception as exc:
            logger.error("Scraping error: %s", exc)
            return []
        finally:
            await self._close_browser()

    async def _collect_property_links(self, max_properties: Optional[int] = None) -> List[str]:
        """Collect property links across pages."""
        all_links = set()
        page_num = 1
        max_pages = 50

        while page_num <= max_pages:
            if page_num == 1:
                url = self.LISTING_URL
            else:
                url = f"{self.LISTING_URL}?page={page_num}"

            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)

                await self._scroll_page()

                links = await self.page.query_selector_all(
                    'a[href*="/imovel/"], a[href*="/lote/"], a[href*="imoveis/"]'
                )

                page_links = set()
                for link in links:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    if "/imovel/" in full_url or "/lote/" in full_url:
                        page_links.add(full_url)

                if not page_links:
                    logger.info("Page %s: no links found, stopping pagination", page_num)
                    break

                new_links = page_links - all_links
                if not new_links:
                    logger.info("Page %s: no new links, stopping pagination", page_num)
                    break

                all_links.update(new_links)
                logger.info("Page %s: +%s links (total: %s)", page_num, len(new_links), len(all_links))

                if max_properties and len(all_links) >= max_properties:
                    break

                page_num += 1

            except Exception as exc:
                logger.warning("Page %s error: %s", page_num, exc)
                break

        return list(all_links)[:max_properties] if max_properties else list(all_links)

    async def _scroll_page(self) -> None:
        """Scroll to load lazy content."""
        try:
            await self.page.evaluate(
                """
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 300;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= document.body.scrollHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                        setTimeout(() => { clearInterval(timer); resolve(); }, 5000);
                    });
                }
                """
            )
            await asyncio.sleep(1)
        except Exception:
            pass

    async def _extract_property(self, url: str) -> Optional[Dict]:
        """Extract property details from a property page."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            property_data = {
                "source_url": url,
                "url": url,
                "auctioneer_url": self.BASE_URL,
                "auctioneer_name": self.AUCTIONEER_NAME,
                "auctioneer_id": self.AUCTIONEER_ID,
                "created_at": datetime.utcnow().isoformat(),
            }

            title_selectors = ["h1", ".property-title", ".titulo", '[class*="title"]']
            for selector in title_selectors:
                elem = await self.page.query_selector(selector)
                if not elem:
                    continue
                text = await elem.inner_text()
                if text and len(text) > 5:
                    property_data["title"] = text.strip()
                    break

            page_text = await self.page.inner_text("body")

            state, city = self._extract_location(page_text, property_data.get("title", ""))
            property_data["state"] = state
            property_data["city"] = city

            property_data["category"] = self._extract_category(page_text, property_data.get("title", ""))

            property_data.update(self._extract_values(page_text))

            img_selectors = [
                "img.property-image",
                ".gallery img",
                '[class*="foto"] img',
                ".carousel img",
                'img[src*="imovel"]',
            ]
            for selector in img_selectors:
                elem = await self.page.query_selector(selector)
                if not elem:
                    continue
                src = await elem.get_attribute("src")
                if src and not any(token in src.lower() for token in ["logo", "icon", "placeholder"]):
                    property_data["image_url"] = src if src.startswith("http") else f"{self.BASE_URL}{src}"
                    break

            area_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m(?:2|\u00b2)", page_text)
            if area_match:
                property_data["area_total"] = float(area_match.group(1).replace(",", "."))

            if any(token in page_text.lower() for token in ["judicial", "vara", "comarca", "processo"]):
                property_data["auction_type"] = "Judicial"
            elif any(token in page_text.lower() for token in ["extrajudicial", "9.514", "9514"]):
                property_data["auction_type"] = "Extrajudicial"
            else:
                property_data["auction_type"] = "Extrajudicial"

            return property_data

        except Exception as exc:
            logger.error("Error extracting %s: %s", url, exc)
            return None

    def _extract_location(self, text: str, title: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract city and state from text."""
        patterns = [
            r"([A-Za-z\s]+)\s*[-/]\s*([A-Z]{2})\b",
            r"\b([A-Z]{2})\s*[-/]\s*([A-Za-z\s]+)",
        ]

        combined = self._normalize_text(f"{title} {text}")

        states = [
            "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
            "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
            "SP", "SE", "TO",
        ]

        for pattern in patterns:
            match = re.search(pattern, combined)
            if not match:
                continue
            g1, g2 = match.groups()
            if g2.upper() in states:
                return g2.upper(), g1.strip().title()
            if g1.upper() in states:
                return g1.upper(), g2.strip().title()

        for state in states:
            if re.search(rf"\b{state}\b", combined):
                return state, None

        return None, None

    def _extract_category(self, text: str, title: str) -> str:
        """Extract property category from text."""
        combined = self._normalize_text(f"{title} {text}").lower()

        categories = {
            "Apartamento": ["apartamento", "apto", "flat", "studio", "kitnet"],
            "Casa": ["casa", "sobrado", "residencia"],
            "Terreno": ["terreno", "lote", "gleba", "area"],
            "Comercial": ["comercial", "loja", "sala", "escritorio", "galpao"],
            "Rural": ["rural", "fazenda", "sitio", "chacara"],
        }

        for category, keywords in categories.items():
            if any(keyword in combined for keyword in keywords):
                return category

        return "Outro"

    def _extract_values(self, text: str) -> Dict:
        """Extract monetary values from page text."""
        values: Dict[str, float] = {}
        normalized_text = self._normalize_text(text)

        patterns = {
            "evaluation_value": [
                r"avaliacao[:\s]*R?\$?\s*([\d.,]+)",
                r"valor\s+de\s+avaliacao[:\s]*R?\$?\s*([\d.,]+)",
            ],
            "first_auction_value": [
                r"1[oa]?\s*(?:leilao|praca)[:\s]*R?\$?\s*([\d.,]+)",
                r"primeiro\s+leilao[:\s]*R?\$?\s*([\d.,]+)",
            ],
            "second_auction_value": [
                r"2[oa]?\s*(?:leilao|praca)[:\s]*R?\$?\s*([\d.,]+)",
                r"segundo\s+leilao[:\s]*R?\$?\s*([\d.,]+)",
            ],
        }

        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, normalized_text, re.IGNORECASE)
                if not match:
                    continue
                value_str = match.group(1).replace(".", "").replace(",", ".")
                try:
                    values[field] = float(value_str)
                    break
                except ValueError:
                    continue

        lance_patterns = [
            r"lance\s*minimo[:\s]*R?\$?\s*([\d.,]+)",
            r"valor\s*minimo[:\s]*R?\$?\s*([\d.,]+)",
        ]
        for pattern in lance_patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if not match:
                continue
            value_str = match.group(1).replace(".", "").replace(",", ".")
            try:
                values["minimum_bid"] = float(value_str)
                break
            except ValueError:
                continue

        if values.get("evaluation_value") and values.get("second_auction_value"):
            discount = (
                (values["evaluation_value"] - values["second_auction_value"])
                / values["evaluation_value"]
            ) * 100
            values["discount_percentage"] = round(discount, 2)

        return values

    def _normalize_text(self, text: str) -> str:
        """Normalize accents for ASCII-friendly matching."""
        normalized = unicodedata.normalize("NFD", text)
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        normalized = normalized.replace("\u00ba", "o").replace("\u00aa", "a")
        return normalized


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = PortalZukScraperV2(headless=False)
    results = scraper.scrape_properties(max_properties=5)
    print("=" * 60)
    print(f"RESULT: {len(results)} properties extracted")
    print("=" * 60)
    for prop in results:
        print(f"- {prop.get('title', 'No title')}")
