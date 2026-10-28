
# BE-07 — Book Record Enrichment API

A FastAPI endpoint that accepts a scraped book record and returns a structured enrichment result. Stage 1 uses a deterministic stub so that input validation and output handling can be tested without making any AI model calls.

## Requirements

- Python 3.10+
- Dependencies installed from `requirements.txt`

## Run the API in stub mode

From the `BE-07 AI API` directory:

```bash
LLM_STUB=1 python -m uvicorn src.api:app --reload --port 8001
```

The stub mode does not call the AI provider.

## Endpoint

`POST /enrich`

### Valid request

```bash
curl -i -X POST http://127.0.0.1:8001/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Example Book",
    "price_gbp": 12.99,
    "availability_text": "In stock",
    "description": "A fictional example for API testing."
  }'
```

Actual response body:

```json
{
  "category": "other",
  "summary": "Book record for The Example Book.",
  "quality_flags": [],
  "confidence": 0.3
}
```

HTTP status: `200 OK`

### Invalid request

This request deliberately omits the required `title` field.

```bash
curl -i -X POST http://127.0.0.1:8001/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "price_gbp": 12.99,
    "availability_text": "In stock"
  }'
```

Actual response body:

```json
{
  "error": "Invalid input",
  "details": [
    {
      "field": "body.title",
      "message": "Field required"
    }
  ]
}
```

HTTP status: `400 Bad Request`

## Output schema

- `category`: `fiction`, `non_fiction`, `children`, `reference`, or `other`.
- `summary`: one non-empty sentence.
- `quality_flags`: permitted flags from the job card.
- `confidence`: a number between `0` and `1`.

The Stage 1 stub returns a deterministic response. Real model integration, versioned prompting, and model-output validation are subsequent stages.

## Environment configuration

The application uses these environment variables for its provider configuration:

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

The `.env` file contains local configuration and must not be committed. Use `.env.example` as the configuration template.
