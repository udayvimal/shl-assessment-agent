"""
Script to scrape the SHL Individual Test Solutions catalog and save to catalog.json.
Run once: python catalog_builder.py

Approach:
  1. Paginate through /product-catalog/?start=N&type=1 (type=1 = Individual Tests)
  2. Extract assessment name, URL, and test-type badges from each page
  3. De-duplicate by URL
  4. Optionally fetch each detail page for a short description
"""
import httpx
import json
import re
import time
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
LIST_URL = "https://www.shl.com/solutions/products/product-catalog/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

TEST_TYPE_LABELS = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}


def _get(url: str, params: dict | None = None) -> httpx.Response | None:
    for attempt in range(3):
        try:
            r = httpx.get(
                url,
                params=params,
                headers=HEADERS,
                follow_redirects=True,
                timeout=30,
            )
            r.raise_for_status()
            return r
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    return None


def _extract_types(cell_or_row) -> list[str]:
    """Extract single-letter type codes from any element."""
    badges = []
    # Try several selector patterns SHL uses
    for sel in [
        "[class*='type'] span",
        "[class*='badge']",
        "span[class*='label']",
        "td:nth-child(4) span",
        "td:nth-child(3) span",
        ".product-type",
        "[data-type]",
    ]:
        for el in cell_or_row.select(sel):
            txt = el.get_text(strip=True)
            if len(txt) == 1 and txt in TEST_TYPE_LABELS:
                badges.append(txt)
        if badges:
            break

    # Fallback: scan ALL spans/divs in the row for single-letter type codes
    if not badges:
        for el in cell_or_row.find_all(["span", "div", "td"]):
            txt = el.get_text(strip=True)
            if len(txt) == 1 and txt in TEST_TYPE_LABELS:
                badges.append(txt)

    return list(dict.fromkeys(badges))  # deduplicate, preserve order


def fetch_page(start: int) -> list[dict]:
    r = _get(LIST_URL, params={"start": start, "type": 1})
    if r is None:
        print(f"  Skipping start={start} (failed)")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items = []

    # --- Strategy 1: table rows containing a product-catalog/view link ---
    for row in soup.find_all("tr"):
        link = row.find("a", href=re.compile(r"/product-catalog/view/"))
        if not link:
            continue
        name = link.get_text(strip=True)
        if not name:
            continue
        href = link["href"]
        url = href if href.startswith("http") else BASE + href
        types = _extract_types(row)
        items.append({"name": name, "url": url, "test_types": types, "description": ""})

    # --- Strategy 2: any div/li containing a product-catalog/view link ---
    if not items:
        for container in soup.find_all(["div", "li", "article"]):
            link = container.find("a", href=re.compile(r"/product-catalog/view/"))
            if not link:
                continue
            name = link.get_text(strip=True)
            if not name:
                continue
            href = link["href"]
            url = href if href.startswith("http") else BASE + href
            types = _extract_types(container)
            items.append({"name": name, "url": url, "test_types": types, "description": ""})

    # --- Strategy 3: bare anchor scan (last resort — loses type info) ---
    if not items:
        for a in soup.find_all("a", href=re.compile(r"/product-catalog/view/")):
            name = a.get_text(strip=True)
            if not name:
                continue
            href = a["href"]
            url = href if href.startswith("http") else BASE + href
            items.append({"name": name, "url": url, "test_types": [], "description": ""})

    return items


def fetch_detail(url: str) -> str:
    """Fetch a short description from the assessment detail page."""
    r = _get(url)
    if r is None:
        return ""
    soup = BeautifulSoup(r.text, "html.parser")
    for sel in [
        ".product-overview p",
        ".product-description p",
        "[class*='overview'] p",
        "[class*='description'] p",
        "main p",
    ]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            if len(text) > 40:
                return text[:400]
    return ""


def main(fetch_descriptions: bool = False) -> None:
    all_items: list[dict] = []
    seen_urls: set[str] = set()

    # SHL catalog has ~377 items; pages of 12 → need up to ~32 pages
    print("Scraping catalog pages (type=1 Individual Test Solutions)…")
    for start in range(0, 32 * 12, 12):
        print(f"  start={start}", end="", flush=True)
        page_items = fetch_page(start)
        new = 0
        for item in page_items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                all_items.append(item)
                new += 1
        print(f"  → {new} new  (total {len(all_items)})")
        if new == 0 and start > 0:
            # Two consecutive empty pages = end of catalog
            print("  No new items — stopping pagination.")
            break
        time.sleep(0.4)

    print(f"\nTotal unique items scraped: {len(all_items)}")

    if fetch_descriptions:
        print("Fetching detail pages for descriptions…")
        for i, item in enumerate(all_items):
            if not item["description"]:
                item["description"] = fetch_detail(item["url"])
                print(f"  [{i+1}/{len(all_items)}] {item['name'][:60]}")
                time.sleep(0.3)

    with open("catalog.json", "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print("Saved → catalog.json")


if __name__ == "__main__":
    import sys
    fetch_desc = "--descriptions" in sys.argv
    main(fetch_descriptions=fetch_desc)
