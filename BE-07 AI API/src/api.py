
import os
from enum import Enum
from typing import Annotated

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(title="Book Record Enrichment API")


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


@app.post("/enrich", response_model=BookEnrichment)
def enrich_book(book: BookInput) -> BookEnrichment:
    if os.getenv("LLM_STUB", "0") == "1":
        return stub_enrichment(book)

    return JSONResponse(
        status_code=503,
        content={
            "error": "Real model integration is not implemented yet. "
            "Use LLM_STUB=1 during Stage 1."
        },
    )
