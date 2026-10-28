
from pathlib import Path
from time import sleep
from urllib.parse import urljoin, urldefrag

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"
TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.5
MAX_CATALOGUE_PAGES = 3

USER_AGENT = (
    "FlyRankInternship-A9/1.0 "
    "(educational scraper; repository: "
    "https://github.com/uzairateef-rgb/backend-internship)"
)


def fetch_html(url: str, cache_file: Path) -> str:
    """Read cached HTML or fetch it once and save a successful response."""
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        print(f"CACHE HIT url={url} bytes={len(html.encode('utf-8'))}")
        return html

    # Be polite before each live request.
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

    return response.content.decode(
        response.encoding or "utf-8",
        errors="replace",
    )


def catalogue_cache_path(page_number: int) -> Path:
    if page_number == 1:
        return CACHE_DIR / "catalogue-page-1.html"
    return CACHE_DIR / f"catalogue-page-{page_number}.html"


def discover_books() -> list[dict[str, str]]:
    current_url = CATALOGUE_URL
    seen_pages: set[str] = set()
    books: list[dict[str, str]] = []

    for page_number in range(1, MAX_CATALOGUE_PAGES + 1):
        if current_url in seen_pages:
            break

        seen_pages.add(current_url)

        html = fetch_html(
            current_url,
            catalogue_cache_path(page_number),
        )
        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):
            link = article.select_one("h3 a")
            if link is None:
                continue

            href = link.get("href")
            if not href:
                continue

            absolute_url = urljoin(current_url, href)
            absolute_url, _fragment = urldefrag(absolute_url)

            books.append({
                "product_url": absolute_url,
                "source_page": current_url,
            })

        next_link = soup.select_one("li.next a")
        if next_link is None:
            break

        next_href = next_link.get("href")
        if not next_href:
            break

        current_url = urljoin(current_url, next_href)

    unique_books: dict[str, dict[str, str]] = {}
    for book in books:
        unique_books.setdefault(book["product_url"], book)

    result = list(unique_books.values())

    print(f"catalogue_pages={len(seen_pages)}")
    print(f"discovered={len(books)}")
    print(f"unique_urls={len(result)}")

    return result


def main() -> None:
    books = discover_books()
    print(f"Discovery complete; books_ready_for_next_stage={len(books)}")


if __name__ == "__main__":
    main()
