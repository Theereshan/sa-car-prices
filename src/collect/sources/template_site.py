"""TEMPLATE — copy this file per website and fill in the TODOs.

How to find the selectors:
  1. Open a search results page in Chrome -> right-click an ad -> Inspect.
  2. Find the element wrapping each ad link; note its tag/class.
  3. Open one ad and do the same for price, year, mileage, etc.
  4. Many sites embed a JSON blob (look for <script type="application/ld+json">)
     — parsing that is far more stable than CSS classes.

Run:  python -m src.collect.sources.template_site --pages 2
"""
import argparse
import json

from bs4 import BeautifulSoup

from src.collect.scraper_base import PoliteScraper


class TemplateSite(PoliteScraper):
    source = "template_site"                     # TODO: short site name
    base_url = "https://www.example.co.za"       # TODO

    def search_page_url(self, page: int) -> str:
        return f"{self.base_url}/used-cars?page={page}"   # TODO

    def parse_search_page(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a.listing-card")             # TODO: selector
        return [self.base_url + a["href"] if a["href"].startswith("/") else a["href"] for a in links]

    def parse_listing(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        # Prefer structured data if the site provides it
        ld = soup.find("script", type="application/ld+json")
        data = json.loads(ld.string) if ld and ld.string else {}

        def text(selector):
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None

        return {
            "listing_id": url.rstrip("/").split("/")[-1],          # TODO: stable ad ID
            "title": data.get("name") or text("h1"),
            "make": (data.get("brand") or {}).get("name"),         # TODO
            "model": data.get("model"),                            # TODO
            "variant": None,
            "year": data.get("vehicleModelDate") or text(".spec-year"),     # TODO
            "mileage": text(".spec-mileage"),                       # TODO — keep raw text, e.g. "85 000 km"
            "price": (data.get("offers") or {}).get("price") or text(".price"),  # TODO
            "fuel_type": data.get("fuelType") or text(".spec-fuel"),
            "transmission": data.get("vehicleTransmission") or text(".spec-transmission"),
            "body_type": data.get("bodyType"),
            "province": text(".location-province"),                 # TODO
            "city": text(".location-city"),                         # TODO
            "seller_type": text(".seller-type"),                    # TODO: 'Dealer' / 'Private'
        }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pages", type=int, default=1)
    n = TemplateSite().run(max_pages=p.parse_args().pages)
    print(f"Done. {n} new listings saved.")
