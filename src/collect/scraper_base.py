"""Polite scraping framework.

Each website gets its own subclass that only knows how to (1) list ad URLs on a
search page and (2) parse one ad page. Rate limiting, robots.txt, retries,
de-duplication and saving are handled here once.

BEFORE scraping any site: read its Terms of Service. If they prohibit scraping,
don't — use a public dataset via import_csv instead.
"""
import time
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests

from src.config import SCRAPER_DELAY_SECONDS, SCRAPER_USER_AGENT
from src.db import insert_raw


class PoliteScraper(ABC):
    source: str          # short name stored in raw_listings.source
    base_url: str        # e.g. "https://www.example.co.za"

    def __init__(self, delay: float = SCRAPER_DELAY_SECONDS):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers["User-Agent"] = SCRAPER_USER_AGENT
        self._last_request = 0.0
        self._robots = RobotFileParser(urljoin(self.base_url, "/robots.txt"))
        self._robots.read()

    # ---- implement these per site ------------------------------------------
    @abstractmethod
    def search_page_url(self, page: int) -> str:
        """URL of results page N."""

    @abstractmethod
    def parse_search_page(self, html: str) -> list[str]:
        """Return absolute URLs of individual ads on a results page."""

    @abstractmethod
    def parse_listing(self, html: str, url: str) -> dict:
        """Return a dict with keys from db.RAW_COLUMNS (listing_id required)."""

    # ---- shared machinery ----------------------------------------------------
    def fetch(self, url: str, retries: int = 3) -> str | None:
        if not self._robots.can_fetch(SCRAPER_USER_AGENT, url):
            print(f"robots.txt disallows {url} — skipping")
            return None
        for attempt in range(1, retries + 1):
            wait = self.delay - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            try:
                r = self.session.get(url, timeout=20)
                if r.status_code == 429:           # told to slow down: back off hard
                    time.sleep(self.delay * 10 * attempt)
                    continue
                r.raise_for_status()
                return r.text
            except requests.RequestException as e:
                print(f"[{attempt}/{retries}] {url}: {e}")
                time.sleep(self.delay * 2 * attempt)
        return None

    def run(self, max_pages: int, flush_every: int = 50) -> int:
        """Crawl pages 1..max_pages. Saves in batches so a crash loses little."""
        batch, total = [], 0
        for page in range(1, max_pages + 1):
            html = self.fetch(self.search_page_url(page))
            if not html:
                continue
            ad_urls = self.parse_search_page(html)
            if not ad_urls:
                print(f"No ads on page {page}; stopping.")
                break
            for url in ad_urls:
                ad_html = self.fetch(url)
                if not ad_html:
                    continue
                try:
                    row = self.parse_listing(ad_html, url)
                except Exception as e:             # one bad ad mustn't kill the run
                    print(f"Parse failed for {url}: {e}")
                    continue
                row.update(source=self.source, url=url)
                batch.append(row)
                if len(batch) >= flush_every:
                    total += insert_raw(pd.DataFrame(batch))
                    batch.clear()
            print(f"Page {page} done — {total} new rows saved so far")
        if batch:
            total += insert_raw(pd.DataFrame(batch))
        return total

    @staticmethod
    def domain(url: str) -> str:
        return urlparse(url).netloc
