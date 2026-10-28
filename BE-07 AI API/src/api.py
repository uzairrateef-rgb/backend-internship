
import json
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated
import random
import time
from email.utils import parsedate_to_datetime

from openai import APIStatusError, APITimeoutError, InternalServerError, RateLimitError, OpenAI, OpenAIError

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError


app = FastAPI(title="Book Record Enrichment API")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

PROMPT_PATH = PROJECT_ROOT / "prompts" / "book-enrichment-v1.md"
PROMPT_VERSION = "book-enrichment-v1"
QUARANTINE_PATH = PROJECT_ROOT / "logs" / "quarantine.jsonl"
COST_LOG_PATH = PROJECT_ROOT / "logs" / "cost.jsonl"

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    timeout=20.0,
    max_retries=0,
)

MODEL = os.environ["LLM_MODEL"]


class BookCategory(str, Enum):
    fiction = "fiction"
    non_fiction = "non_fiction"
    children = "children"
    reference = "reference"
    other = "other"


class QualityFlag(str, Enum):
    missing_description = "missing_description"
    unusual_price = "unusual_price"
    unclear_category = "unclear_category"


class BookInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(min_length=1, max_length=200)]
    price_gbp: float
    availability_text: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(max_length=2000)] = ""


class BookEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: BookCategory
    summary: Annotated[str, Field(min_length=1)]
    quality_flags: list[QualityFlag]
    confidence: Annotated[float, Field(ge=0, le=1)]


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = []

    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
        })

    return JSONResponse(
        status_code=400,
        content={"error": "Invalid input", "details": errors},
    )


def stub_enrichment(book: BookInput) -> BookEnrichment:
    flags = []

    if not book.description.strip():
        flags.append(QualityFlag.missing_description)

    return BookEnrichment(
        category=BookCategory.other,
        summary=f"Book record for {book.title}.",
        quality_flags=flags,
        confidence=0.3,
    )


def parse_json_object(raw_output: str) -> dict:
    """Parse a JSON object, allowing Markdown fences or surrounding text."""
    text = raw_output.strip()

    # First, try the entire response as JSON.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("The JSON response must be an object.")
    except json.JSONDecodeError:
        pass

    # If the model wrapped JSON in text or Markdown, find a JSON object.
    decoder = json.JSONDecoder()
    for position, character in enumerate(text):
        if character != "{":
            continue

        try:
            parsed, _ = decoder.raw_decode(text[position:])
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    raise ValueError("No valid JSON object was found in the model response.")


def validate_model_output(raw_output: str) -> BookEnrichment:
    """Parse model text and validate every output field against the schema."""
    parsed = parse_json_object(raw_output)
    return BookEnrichment.model_validate(parsed)


def quarantine_failure(
    book: BookInput,
    raw_output: str,
    validation_error: str,
    repair_output: str,
) -> None:
    """Append one JSON record for an output that failed both attempts."""
    QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": MODEL,
        "input": book.model_dump(mode="json"),
        "raw_output": raw_output,
        "validation_error": validation_error,
        "repair_output": repair_output,
    }

    with QUARANTINE_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def retry_after_seconds(error: APIStatusError) -> float | None:
    """Read Retry-After as seconds or as an HTTP date."""
    response = error.response
    value = response.headers.get("retry-after")

    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            return max(
                0.0,
                (retry_at - datetime.now(timezone.utc)).total_seconds(),
            )
        except (TypeError, ValueError, OverflowError):
            return None


def log_model_call(
    *,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
    repair_count: int,
) -> None:
    """Append usage and timing information as one JSONL record."""
    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": MODEL,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "repair_count": repair_count,
    }

    with COST_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def request_model(
    messages: list[dict],
    repair_count: int = 0,
) -> str:
    """Call the model with explicit retry rules and usage logging."""
    delays = (1, 2, 4)
    started = time.monotonic()

    for attempt in range(4):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0,
                max_tokens=300,
            )
            break

        except APITimeoutError:
            if attempt == 3:
                raise
            time.sleep(delays[attempt] + random.uniform(0, 0.25))

        except (RateLimitError, InternalServerError) as error:
            if attempt == 3:
                raise

            retry_after = retry_after_seconds(error)
            delay = (
                retry_after
                if retry_after is not None
                else delays[attempt] + random.uniform(0, 0.25)
            )
            time.sleep(delay)

        except APIStatusError as error:
            # Retry other HTTP 5xx responses, but not 4xx responses.
            if error.status_code < 500 or attempt == 3:
                raise

            retry_after = retry_after_seconds(error)
            delay = (
                retry_after
                if retry_after is not None
                else delays[attempt] + random.uniform(0, 0.25)
            )
            time.sleep(delay)

    answer = response.choices[0].message.content or ""
    usage = response.usage

    log_model_call(
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        duration_ms=round((time.monotonic() - started) * 1000),
        repair_count=repair_count,
    )

    return answer


def enrich_with_model(book: BookInput) -> BookEnrichment | JSONResponse:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_message = json.dumps(
        book.model_dump(mode="json"),
        ensure_ascii=False,
    )

    original_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw_output = request_model(original_messages, repair_count=0)
    except OpenAIError:
        return JSONResponse(
            status_code=503,
            content={"error": "The model provider is temporarily unavailable."},
        )

    try:
        return validate_model_output(raw_output)
    except (ValueError, ValidationError, json.JSONDecodeError) as first_error:
        validation_error = str(first_error)

    # Exactly one repair request is allowed.
    repair_message = (
        "Your previous response did not satisfy the required JSON output. "
        "Return only one corrected JSON object that follows the system prompt. "
        "Do not add Markdown fences or commentary.\n\n"
        f"Original input JSON:\n{user_message}\n\n"
        f"Rejected model output:\n{raw_output}\n\n"
        f"Exact parsing/validation error:\n{validation_error}"
    )

    repair_output = ""
    try:
        repair_output = request_model(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": repair_message},
        ],
    repair_count=1,
)
        return validate_model_output(repair_output)
    except (ValueError, ValidationError, json.JSONDecodeError) as repair_error:
        quarantine_failure(
            book=book,
            raw_output=raw_output,
            validation_error=(
                f"First attempt: {validation_error}\n"
                f"Repair attempt: {repair_error}"
            ),
            repair_output=repair_output,
        )
    except OpenAIError:
        return JSONResponse(
            status_code=503,
            content={"error": "The model provider is temporarily unavailable."},
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "Model output could not be validated after one repair attempt.",
                "prompt_version": PROMPT_VERSION,
            },
        )


@app.post("/enrich", response_model=None)
def enrich_book(book: BookInput):
    if os.getenv("LLM_ENABLED", "true").strip().lower() == "false":
        return stub_enrichment(book)

    if os.getenv("LLM_STUB", "0") == "1":
        return stub_enrichment(book)

    return enrich_with_model(book)
