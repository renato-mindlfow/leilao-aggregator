"""
Scraper para LF Leiloes.
Usa MultiLayerFetcher (ScrapingBee quando necessario) + BeautifulSoup.
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


class LfReiloesScraper:
    BASE_URL = "https://www.lfleiloesmt.com.br"
    LISTING_URL = BASE_URL
    FALLBACK_LISTING_URL = "https://lfleiloesmt-lanceslotes.cheetah.builderall.com/"
    AUCTIONEER_ID = "lfreiloes"
    AUCTIONEER_NAME = "LF Leiloes"

    def __init__(self):
        self.fetcher = MultiLayerFetcher(timeout=60.0, min_content_length=1200)

    def scrape_properties(self, max_properties: int = 5) -> List[Dict]:
        properties: List[Dict] = []
        logger.info("Iniciando scraping de LF Leiloes")

        links = self._collect_listing_links([self.LISTING_URL, self.FALLBACK_LISTING_URL])
        if not links:
            logger.warning("Nenhum link encontrado na listagem")
            return []

        for link in links:
            if len(properties) >= max_properties:
                break
            prop = self._extract_property_details(link)
            if prop:
                properties.append(prop)

        logger.info("Scraping concluido: %s imoveis", len(properties))
        return properties

    def _collect_listing_links(self, urls: List[str]) -> List[str]:
        candidates: List[str] = []
        for url in urls:
            result = self._fetch_html(url)
            if not result:
                continue
            soup = BeautifulSoup(result, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if any(token in href for token in ["/imovel", "/lote", "/leilao"]):
                    full_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)
                    candidates.append(full_url)

        unique_links = list(dict.fromkeys(candidates))
        if unique_links:
            return unique_links[:50]

        return asyncio.run(self._collect_links_playwright(urls))

    async def _collect_links_playwright(self, urls: List[str]) -> List[str]:
        candidates: List[str] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            for url in urls:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(5)
                    links = await page.query_selector_all("a[href]")
                    for link in links:
                        href = await link.get_attribute("href")
                        if href and any(token in href for token in ["/imovel", "/lote", "/leilao"]):
                            full_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)
                            candidates.append(full_url)
                except Exception:
                    continue
            await browser.close()

        return list(dict.fromkeys(candidates))[:50]

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
        title_tag = soup.find("h1")
        if title_tag:
            return title_tag.get_text(strip=True)
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
        match = re.search(r"([A-Za-zÀ-ÿ\s]+)\s*[-/]\s*([A-Z]{2})\b", title)
        if match:
            return match.group(1).strip().title(), match.group(2).upper()
        match = re.search(r"([A-Za-zÀ-ÿ\s]+)\s*/\s*([A-Z]{2})\b", text)
        if match:
            return match.group(1).strip().title(), match.group(2).upper()
        return None, None
