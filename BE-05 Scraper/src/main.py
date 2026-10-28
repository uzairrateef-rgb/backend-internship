
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_FILE = CACHE_DIR / "catalogue-page-1.html"

CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"
TIMEOUT_SECONDS = 10

USER_AGENT = (
    "FlyRankInternship-A9/1.0 "
    "(educational scraper; repository: "
    "https://github.com/uzairateef-rgb/backend-internship)"
)


def fetch_catalogue_page() -> str:
    """Fetch the first catalogue page once and reuse its cached HTML."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if CACHE_FILE.exists():
        html = CACHE_FILE.read_text(encoding="utf-8")
        size = len(html.encode("utf-8"))
        print(f"CACHE HIT status=200 bytes={size}")
        return html

    response = requests.get(
        CATALOGUE_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )

    print(f"HTTP status={response.status_code}")

    # Never parse or cache a failed HTTP response.
    if response.status_code != 200:
        response.raise_for_status()
        raise RuntimeError(
            f"Expected HTTP 200, received {response.status_code}"
        )

    CACHE_FILE.write_bytes(response.content)

    print(f"FETCH status=200 bytes={len(response.content)}")
    print(f"Saved HTML to {CACHE_FILE.relative_to(PROJECT_ROOT)}")

    return response.content.decode(
        response.encoding or "utf-8",
        errors="replace",
    )


def main() -> None:
    html = fetch_catalogue_page()
    print(f"HTML loaded successfully; characters={len(html)}")


if __name__ == "__main__":
    main()
