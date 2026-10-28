
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from urllib.parse import urldefrag, urljoin
import hashlib
from urllib.parse import urldefrag, urljoin, urlparse
import json
import re
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"

CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"
TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.5
MAX_CATALOGUE_PAGES = 3

USER_AGENT = (
    "FlyRankInternship-A9/1.0 "
    "(educational scraper; repository: "
    "https://github.com/uzairateef-rgb/backend-internship)"
)


def fetch_html(url: str, cache_file: Path) -> tuple[str, bool]:
    """Return HTML and whether it was read from cache."""
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        print(f"CACHE HIT url={url} bytes={len(html.encode('utf-8'))}")
        return html, True

    sleep(REQUEST_DELAY_SECONDS)
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    print(f"HTTP status={response.status_code} url={url}")

    if response.status_code != 200:
        response.raise_for_status()
        raise RuntimeError(
            f"Expected HTTP 200 for {url}, got {response.status_code}"
        )

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(response.content)
    print(f"FETCH status=200 url={url} bytes={len(response.content)}")

    html = response.content.decode(
        response.encoding or "utf-8",
        errors="replace",
    )
    return html, False


def catalogue_cache_path(page_number: int) -> Path:
    return CACHE_DIR / f"catalogue-page-{page_number}.html"


def detail_cache_path(product_url: str) -> Path:
    path_parts = urlparse(product_url).path.rstrip("/").split("/")

    # Book URLs end in /index.html, so use the preceding folder as the slug.
    slug = (
        path_parts[-2]
        if path_parts[-1] == "index.html" and len(path_parts) > 1
        else path_parts[-1]
    )

    safe_slug = "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in slug
    )

    # Ensure every distinct product URL gets its own cache file.
    url_hash = hashlib.sha256(product_url.encode("utf-8")).hexdigest()[:12]

    return CACHE_DIR / "books" / f"{safe_slug}-{url_hash}.html"

def discover_books() -> list[dict[str, str]]:
    current_url = CATALOGUE_URL
    seen_pages: set[str] = set()
    books: list[dict[str, str]] = []

    for page_number in range(1, MAX_CATALOGUE_PAGES + 1):
        if current_url in seen_pages:
            break
        seen_pages.add(current_url)

        html, _ = fetch_html(
            current_url,
            catalogue_cache_path(page_number),
        )
        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):
            link = article.select_one("h3 a")
            href = link.get("href") if link else None
            if not href:
                continue

            product_url = urljoin(current_url, href)
            product_url, _ = urldefrag(product_url)
            books.append({
                "product_url": product_url,
                "source_page": current_url,
            })

        next_link = soup.select_one("li.next a")
        next_href = next_link.get("href") if next_link else None
        if not next_href:
            break

        current_url = urljoin(current_url, next_href)

    unique: dict[str, dict[str, str]] = {}
    for book in books:
        unique.setdefault(book["product_url"], book)

    print(f"catalogue_pages={len(seen_pages)}")
    print(f"discovered={len(books)}")
    print(f"unique_urls={len(unique)}")
    return list(unique.values())


def extract_book(
    product_url: str,
    source_page: str,
) -> dict:
    """Extract the eight raw fields from one book detail page."""
    html, from_cache = fetch_html(
        product_url,
        detail_cache_path(product_url),
    )
    soup = BeautifulSoup(html, "html.parser")

    product = soup.select_one("article.product_page")
    if product is None:
        raise ValueError("Book detail page has no product article")

    title_element = product.select_one("div.product_main h1")
    price_element = product.select_one("p.price_color")
    availability_element = product.select_one("p.instock.availability")
    rating_element = product.select_one("p.star-rating")

    description_heading = soup.select_one("#product_description")
    description_element = (
        description_heading.find_next_sibling("p")
        if description_heading
        else None
    )

    rating_text = None
    if rating_element:
        rating_classes = rating_element.get("class", [])
        rating_text = next(
            (value for value in rating_classes if value != "star-rating"),
            None,
        )
        if rating_text:
            rating_text = rating_text.capitalize()

    return {
        "title": title_element.get_text(strip=True) if title_element else None,
        "product_url": product_url,
        "price_text": price_element.get_text(strip=True) if price_element else None,
        "availability_text": (
            availability_element.get_text(" ", strip=True)
            if availability_element else None
        ),
        "rating_text": rating_text,
        "description": (
            description_element.get_text(" ", strip=True)
            if description_element else None
        ),
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


class BookRecord(BaseModel):
    title: str = Field(min_length=1)
    product_url: HttpUrl
    price_text: str = Field(min_length=1)
    price_gbp: float = Field(ge=0)
    availability_text: str = Field(min_length=1)
    rating_text: str | None = None
    description: str | None = None
    source_page: HttpUrl
    fetched_at: datetime

    @field_validator("title", "price_text", "availability_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be blank")
        return value.strip()


def normalize_price(price_text: str) -> float:
    match = re.search(r"£\s*(\d+(?:\.\d{1,2})?)", price_text)

    if not match:
        raise ValueError(f"Could not parse GBP price: {price_text!r}")

    return float(match.group(1))


def validate_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    valid_records = []
    invalid_records = []
    seen_urls = set()

    for record in records:
        try:
            normalized = dict(record)

            # Canonicalize product URL identity by removing fragments
            # and normalizing the trailing slash.
            normalized_url = normalized["product_url"].split("#", 1)[0]
            normalized_url = normalized_url.rstrip("/") + "/"
            normalized["product_url"] = normalized_url

            if normalized_url in seen_urls:
                continue

            normalized["price_gbp"] = normalize_price(
                normalized["price_text"]
            )

            validated = BookRecord.model_validate(normalized)
            valid_records.append(validated.model_dump(mode="json"))
            seen_urls.add(normalized_url)

        except (ValidationError, ValueError, KeyError, TypeError) as exc:
            invalid_records.append({
                "record": record,
                "reason": str(exc),
            })

    return valid_records, invalid_records


def write_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

def main() -> None:
    books = discover_books()
    records = []
    failed_pages = 0

    for index, book in enumerate(books, start=1):
        try:
            record = extract_book(
                product_url=book["product_url"],
                source_page=book["source_page"],
            )
            records.append(record)
            print(f"EXTRACTED {index}/{len(books)}: {record['title']}")
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            failed_pages += 1
            print(f"SKIPPED url={book['product_url']} reason={exc}")

    print(f"detail_pages={len(records)}")
    print(f"failed_pages={failed_pages}")

    valid_records, invalid_records = validate_records(records)

    write_json(PROJECT_ROOT / "output" / "books.json", valid_records)
    write_json(PROJECT_ROOT / "output" / "errors.json", invalid_records)

    print(f"valid_records={len(valid_records)}")
    print(f"invalid_records={len(invalid_records)}")
    print(f"output/books.json: {len(valid_records)} records")
    print(f"output/errors.json: {len(invalid_records)} errors")

    if records:
        print("Sample raw record:")
        print(records[0])


if __name__ == "__main__":
    main()
