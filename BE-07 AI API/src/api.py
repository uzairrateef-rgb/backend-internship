import os
from enum import Enum
from typing import Annotated
import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi.responses import PlainTextResponse
from openai import OpenAI
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(title="Book Record Enrichment API")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

PROMPT_PATH = PROJECT_ROOT / "prompts" / "book-enrichment-v1.md"
PROMPT_VERSION = "book-enrichment-v1"

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


@app.post("/enrich", response_model=None)
def enrich_book(book: BookInput):
    if os.getenv("LLM_STUB", "0") == "1":
        return stub_enrichment(book)

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    user_message = json.dumps(
        book.model_dump(),
        ensure_ascii=False,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        temperature=0,
        max_tokens=300,
    )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError("The model returned an empty response.")

    return PlainTextResponse(answer)