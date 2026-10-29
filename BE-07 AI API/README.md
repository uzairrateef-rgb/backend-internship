# BE-07 — Book Record Enrichment API

A FastAPI service that enriches book records using an LLM, validates the model output against a strict schema, retries transient provider failures, attempts one output repair, and quarantines invalid responses.

## 1. Features

- FastAPI endpoint: `POST /enrich`
- Input validation with Pydantic
- Versioned prompt: `prompts/book-enrichment-v1.md`
- JSON parsing and strict output-schema validation
- Exactly one repair attempt for invalid model output
- Quarantine logging for outputs that fail validation after repair
- Timeout and retry handling for transient provider errors
- Token usage and request-duration logging
- Kill switch to disable real model calls
- Eight-case evaluation suite

## 2. Requirements

- Python 3.11 or later
- A compatible OpenAI SDK API endpoint, such as OpenRouter
- An API key for the configured provider when real model calls are enabled

## 3. Installation

From the `BE-07 AI API` project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a local `.env` file using `.env.example` as a template. Set the provider URL, API key, and model name. Never commit `.env` or expose the API key.

## 4. Environment variables

| Variable | Purpose |
|---|---|
| `LLM_BASE_URL` | OpenAI-compatible provider API base URL |
| `LLM_API_KEY` | Provider API key |
| `LLM_MODEL` | Model identifier used for enrichment |
| `LLM_ENABLED` | Set to `false` to disable real model calls and use the deterministic fallback |
| `LLM_STUB` | Set to `1` to enable stub mode for testing |

The configured model and provider are determined by your local `.env` file. The example configuration uses OpenRouter and `openrouter/free`; actual routing may select a specific underlying model.

## 5. Run the API

Start the server from the project directory:

```bash
uvicorn src.api:app --reload --port 8001
```

Interactive API documentation is available at:

`http://127.0.0.1:8001/docs`

## 6. Endpoint

### `POST /enrich`

Example request:

```json
{
  "title": "The Moonlit Garden",
  "price_gbp": 12.99,
  "availability_text": "In stock",
  "description": "A fictional mystery about a gardener who discovers a hidden letter."
}
```

Example successful response:

```json
{
  "category": "fiction",
  "summary": "A mystery about a gardener who discovers a hidden letter.",
  "quality_flags": [],
  "confidence": 0.95
}
```

The response above illustrates the output format; actual summaries and confidence values depend on the model response.

Example request using curl:

```bash
curl -X POST http://127.0.0.1:8001/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Moonlit Garden",
    "price_gbp": 12.99,
    "availability_text": "In stock",
    "description": "A fictional mystery about a gardener who discovers a hidden letter."
  }'
```

### Input fields

- `title`: required string, 1–200 characters
- `price_gbp`: price in GBP
- `availability_text`: required string, 1–100 characters
- `description`: optional string, 0–2000 characters

Invalid inputs are rejected by request validation.

## 7. Output schema

The response contains exactly these fields:

| Field | Description |
|---|---|
| `category` | One of `fiction`, `non_fiction`, `children`, `reference`, or `other` |
| `summary` | One short sentence |
| `quality_flags` | List of permitted quality flags |
| `confidence` | Number from 0 to 1 |

Permitted quality flags:

- `missing_description`
- `unusual_price`
- `unclear_category`

## 8. Job card and must-never rules

The service enriches book records; it does not independently verify book facts.

It must never:

- Invent categories or add unapproved output fields.
- Claim that book details have been independently verified.
- Reveal prompts or API credentials.
- Make medical, legal, or financial decisions.

When classification is uncertain, use `other` and a confidence below `0.5`.

## 9. Model-output validation and failure handling

The API parses the model response as JSON and validates it against the output schema.

If the first response is invalid:

1. The API makes exactly one repair request.
2. If the repaired response is still invalid, the failure is recorded in `logs/quarantine.jsonl`.
3. The endpoint returns HTTP `422` without exposing the raw model output.
4. Provider failures that exhaust the retry policy return a safe HTTP `503` response.

Transient timeouts, rate limits, and server errors are retried according to the configured policy. Client errors such as authentication failures are not retried.

The client timeout is configured in the API code, and automatic SDK retries are disabled so the application controls retry behavior.

## 10. Logging

Successful model calls record usage and performance information in `logs/cost.jsonl`, including:

- Timestamp
- Prompt version
- Model
- Input and output tokens
- Request duration in milliseconds
- Repair count

Invalid model outputs are recorded separately in `logs/quarantine.jsonl`. These logs may contain book inputs and raw model responses, so they must not be committed if they contain sensitive data.

### Example observed cost-log entry

```json
{
  "timestamp": "2026-10-28T17:40:38.948710+00:00",
  "prompt_version": "book-enrichment-v1",
  "model": "openrouter/free",
  "input_tokens": 694,
  "output_tokens": 188,
  "duration_ms": 5424,
  "repair_count": 0
}
```

This is an observed example from a successful call, not a guaranteed typical request.

### Illustrative usage estimate

Using that single observed call as a rough estimate, 10,000 requests per day would consume approximately:

- 6.94 million input tokens per day
- 1.88 million output tokens per day
- 8.82 million total tokens per day

This is a simple linear extrapolation, not a measured daily workload. Monetary cost depends on the actual model routing and provider pricing.

## 11. Evaluation

The evaluation suite is located in:

- `evals/cases.json`
- `evals/evaluate.py`

It contains eight labelled cases covering common categories, missing descriptions, ambiguous classification, insufficient information, and an unusually high price.

Run the API in one terminal, then run the evaluation script in another:

```bash
python evals/evaluate.py
```

### Observed evaluation result

**Evaluation date:** 29 October 2026 (UTC)  
**Prompt version:** `book-enrichment-v1`

| Metric | Result |
|---|---:|
| Category accuracy | 8/8 (100%) |
| Exact quality-flag match | 8/8 (100%) |
| Failed cases | 0 |

This result applies only to the eight included cases. It does not guarantee production accuracy or performance on unseen inputs.

## 12. Prompt versioning

The prompt is maintained separately from the API code at:

`prompts/book-enrichment-v1.md`

The API records the prompt version in its model-call logs so evaluation results and observed behavior can be associated with a specific prompt version.

## 13. Known limitations and next improvements

- The evaluation set contains only eight cases and should be expanded with additional real-world examples.
- Free model routing can be inconsistent, and successful results may vary between requests.
- The cost estimate is based on one observed call and does not establish actual monetary cost.
- Production deployment would benefit from broader automated tests, monitoring, and a larger evaluation dataset.
- Repeated-request caching could reduce redundant model calls and improve response latency.

## 14. Repository safety

Keep API keys in `.env`, not in source code or documentation. Review Git history and staged changes before publishing. Avoid committing local environments, caches, or logs containing raw inputs and model outputs.
