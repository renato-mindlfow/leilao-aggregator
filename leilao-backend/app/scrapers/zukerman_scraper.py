"""
Scraper para Zukerman.
Usa MultiLayerFetcher + BeautifulSoup para extrair links e detalhes.
"""
import logging
import re
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.utils.fetcher import MultiLayerFetcher

logger = logging.getLogger(__name__)


class ZukermanScraper:
    BASE_URL = "https://www.zukerman.com.br"
    LISTING_URL = f"{BASE_URL}/imoveis"
    AUCTIONEER_ID = "zukerman"
    AUCTIONEER_NAME = "Zukerman"

    def __init__(self):
        self.fetcher = MultiLayerFetcher(timeout=60.0, min_content_length=1200)

    def scrape_properties(self, max_properties: int = 5) -> List[Dict]:
        properties: List[Dict] = []
        links = self._collect_listing_links(max_pages=3)
        if not links:
            logger.warning("Nenhum link encontrado na listagem Zukerman")
            return self._scrape_via_portal_zuk(max_properties)

        for link in links:
            if len(properties) >= max_properties:
                break
            prop = self._extract_property_details(link)
            if prop:
                properties.append(prop)

        if not properties or all("portalzuk" in (p.get("source_url") or "") for p in properties):
            return self._scrape_via_portal_zuk(max_properties)

        logger.info("Scraping Zukerman concluido: %s imoveis", len(properties))
        return properties

    def _scrape_via_portal_zuk(self, max_properties: int) -> List[Dict]:
        """Fallback: reutiliza dados do Portal Zuk."""
        try:
            from app.scrapers.portalzuk_scraper_v2 import PortalZukScraperV2

            scraper = PortalZukScraperV2()
            props = scraper.scrape_properties(max_properties=max_properties)
            for prop in props:
                prop["auctioneer_id"] = self.AUCTIONEER_ID
                prop["auctioneer_name"] = self.AUCTIONEER_NAME
                prop["source"] = self.AUCTIONEER_ID
            return props
        except Exception as exc:
            logger.error("Fallback Portal Zuk falhou: %s", exc)
            return []

    def _collect_listing_links(self, max_pages: int = 3) -> List[str]:
        links: List[str] = []
        for page in range(1, max_pages + 1):
            url = self.LISTING_URL if page == 1 else f"{self.LISTING_URL}?p={page}"
            html = self._fetch_html(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if any(token in href for token in ["/leilao", "/imovel", "/lote"]):
                    full_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)
                    links.append(full_url)

            if len(links) >= 50:
                break

        unique_links = list(dict.fromkeys(links))
        if unique_links:
            return unique_links

        return asyncio.run(self._collect_links_playwright(max_pages))

    async def _collect_links_playwright(self, max_pages: int) -> List[str]:
        links: List[str] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            for page_num in range(1, max_pages + 1):
                url = self.LISTING_URL if page_num == 1 else f"{self.LISTING_URL}?p={page_num}"
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(5)
                    anchors = await page.query_selector_all("a[href]")
                    for anchor in anchors:
                        href = await anchor.get_attribute("href")
                        if href and any(token in href for token in ["/leilao", "/imovel", "/lote"]):
                            full_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)
                            links.append(full_url)
                except Exception:
                    continue
            await browser.close()

        return list(dict.fromkeys(links))

    def _extract_property_details(self, url: str) -> Optional[Dict]:
        html = self._fetch_html(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        title = self._extract_title(soup)
        if not title:
            return None

        page_text = soup.get_text(" ", strip=True)
        price = self._extract_price(page_text)
        city, state = self._extract_city_state(title, page_text)

        return {
            "title": title,
            "city": city or "Não informado",
            "state": state or "NI",
            "price": price,
            "source": self.AUCTIONEER_ID,
            "auctioneer_id": self.AUCTIONEER_ID,
            "auctioneer_name": self.AUCTIONEER_NAME,
            "auctioneer_url": self.BASE_URL,
            "source_url": url,
            "url": url,
            "scraped_at": datetime.now().isoformat(),
        }

    def _fetch_html(self, url: str) -> Optional[str]:
        result = asyncio.run(self.fetcher.fetch(url))
        html = result.content if result.success else ""
        return html if html else None

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> Optional[str]:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title.get("content").strip()
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        return None

    @staticmethod
    def _extract_price(text: str) -> Optional[float]:
        match = re.search(r"R\$\s*([\d\.,]+)", text)
        if not match:
            return None
        price_str = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(price_str)
        except ValueError:
            return None

    @staticmethod
    def _extract_city_state(title: str, text: str) -> Tuple[Optional[str], Optional[str]]:
        matches = re.findall(r"([A-Za-zÀ-ÿ\s]{2,40})\s*-\s*([A-Z]{2})\b", text)
        if matches:
            for city, state in reversed(matches):
                if any(token in city.lower() for token in ["cidade", "menor", "maior", "lancamento"]):
                    continue
                city = city.strip()
                city = re.sub(
                    r"^(Apartamento|Casa|Terreno|Imovel|Imóvel|Lote|Sala|Comercial|Prédio|Predio)\s+",
                    "",
                    city,
                    flags=re.IGNORECASE,
                ).strip()
                return city.title(), state.upper()

        parts = [part.strip() for part in title.split("-") if part.strip()]
        for i in range(len(parts) - 1, 0, -1):
            candidate_state = parts[i]
            if len(candidate_state) == 2 and candidate_state.isupper():
                city = parts[i - 1]
                if "cidade" in city.lower():
                    tokens = city.split()
                    if tokens:
                        city = " ".join(tokens[-2:]) if len(tokens) >= 2 else tokens[-1]
                city = re.sub(
                    r"^(Apartamento|Casa|Terreno|Imovel|Imóvel|Lote|Sala|Comercial|Prédio|Predio)\s+",
                    "",
                    city,
                    flags=re.IGNORECASE,
                ).strip()
                return city.title(), candidate_state.upper()

        match = re.search(r"([A-Za-zÀ-ÿ\s]+)\s*/\s*([A-Z]{2})\b", text)
        if match:
            return match.group(1).strip().title(), match.group(2).upper()
        return None, None
