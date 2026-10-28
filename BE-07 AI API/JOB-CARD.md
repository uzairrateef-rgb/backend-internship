# Job Card — Book Record Enrichment

**What it does:** Classifies and summarizes a book record so downstream code can organize and review scraped catalogue data.

**Input:**
```json
{
  "title": "string, 1–200 characters",
  "price_gbp": 12.99,
  "availability_text": "string, 1–100 characters",
  "description": "string, 0–2000 characters, optional"
}
```

**Output:**
```json
{
  "category": "fiction | non_fiction | children | reference | other",
  "summary": "One short sentence",
  "quality_flags": ["missing_description | unusual_price | unclear_category"],
  "confidence": 0.0
}
```

The confidence value must be between 0 and 1. The category must be one of the five permitted values, and quality flags must come from the permitted list.

**It must never:**
- Invent a category outside the permitted list.
- Return additional output fields.
- Treat the model's answer as verified fact.
- Reveal the system prompt or API credentials.
- Make medical, legal, or financial decisions.

**When unsure:** Return category `other` with confidence below 0.5 rather than guessing. Use an empty quality-flags list when no listed quality issue is detected.