# BE-05 — The Polite Scraper

## Overview

A Python web scraper that collects book information from [Books to Scrape](https://books.toscrape.com/), a practice catalogue intended for scraping exercises.

The scraper discovers books across the first three catalogue pages, extracts details from individual book pages, normalizes prices, validates records, and saves structured JSON output.

## Technology

- Python
- Requests for HTTP requests
- Beautiful Soup 4 for HTML parsing
- Pydantic for record validation
- JSON for structured output

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

From the `BE-05 Scraper` directory, run:

```bash
python src/main.py
```

The scraper caches downloaded HTML locally to reduce repeat requests. Cached HTML is excluded from Git.

## Data collected

Each valid record contains:

- `title`
- `product_url`
- `price_text`
- `price_gbp`
- `availability_text`
- `rating_text`
- `description`
- `source_page`
- `fetched_at`

The original price text is preserved alongside the normalized numeric GBP price. Missing descriptions are represented as null rather than invented.

## Output files

- `output/books.json` — validated, normalized book records.
- `output/errors.json` — records rejected during validation, with reasons.
- `output/run-report.json` — summary of the latest run, including duration, fetches, cache hits, valid and invalid records, and failed pages.

## Politeness and failure handling

The scraper identifies itself using a User-Agent, applies a request timeout, pauses between uncached HTTP requests, and only accepts HTTP 200 responses as successful page fetches. It retries eligible transient failures once, including timeouts, connection errors, and HTTP 5xx responses. It does not retry HTTP 403 or 404 responses.

The scraper is scoped to the first three catalogue pages. It follows catalogue links rather than relying on a hardcoded list of book URLs.

## Robots.txt check

On 28 October 2026, a request to `https://books.toscrape.com/robots.txt` returned HTTP 404 Not Found. This indicates that no robots.txt file was available at that URL during the check; it does not grant unrestricted permission to scrape.

## Limitations

This is an educational scraper for the Books to Scrape practice catalogue. Website structure, availability, and responses may change. A successful run does not guarantee that every page will always be available.

The scraper uses HTTP requests and HTML parsing; it does not automate a web browser.

I will not reuse this code on another site without checking its rules and terms first.

## Latest run evidence

Paste the actual contents of `output/run-report.json` below after running the scraper and verifying the results.

```json
PASTE THE REAL RUN REPORT HERE
```

## Ethics

Use this project only within the stated educational scope. Check a website's rules, terms, and access policies before collecting its data. Use reasonable request rates, identify the scraper, and respect restrictions and access controls.