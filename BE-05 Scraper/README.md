# BE-05 Scraper — The Polite Scraper

A Python scraping pipeline that collects book data from the Books to Scrape practice sandbox, normalizes the values, validates records, and stores clean JSON.

## Target classification

- **Target:** [Books to Scrape](https://books.toscrape.com/)
- **Purpose:** Educational scraping practice using a public sandbox designed for this activity.
- **Scope:** The first three catalogue pages only, with book detail URLs discovered from those pages.
- **Data collected:** Book title, canonical product URL, original price text, availability text, rating text, description, source catalogue URL, and fetch timestamp.
- **Robots check:** On 28 October 2026, requesting `https://books.toscrape.com/robots.txt` returned HTTP 404 Not Found. This means no robots file was available at that URL; it does not grant unrestricted permission.
- **Politeness:** The scraper will identify itself with a descriptive User-Agent, use request timeouts, wait at least 500 ms between live requests, check HTTP status codes, and cache fetched HTML during development.

I will not reuse this code on another site without checking its rules and terms first.

## Technology

- Python
- Requests
- Beautiful Soup
- Pydantic
- JSON

## Ethics

Use an official API when one exists. Never bypass logins, paywalls, or blocks. Collect only the data needed for the stated purpose.
