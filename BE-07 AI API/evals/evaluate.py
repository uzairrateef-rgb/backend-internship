import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = PROJECT_ROOT / "evals" / "cases.json"
PROMPT_VERSION = "book-enrichment-v1"


def send_request(url: str, book_input: dict) -> tuple[int, dict]:
    payload = json.dumps(book_input).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=65) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            parsed_body = json.loads(body)
        except json.JSONDecodeError:
            parsed_body = {"error": body}
        return error.code, parsed_body


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the Book Record Enrichment API."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8001/enrich",
        help="Enrichment endpoint URL (default: local port 8001).",
    )
    args = parser.parse_args()

    with CASES_PATH.open(encoding="utf-8") as file:
        cases = json.load(file)

    if len(cases) != 8:
        print(f"ERROR: expected exactly 8 cases; found {len(cases)}.")
        return 1

    category_correct = 0
    category_evaluated = 0
    flag_exact_matches = 0
    flag_evaluated = 0
    failures = []

    print(f"Evaluation date (UTC): {datetime.now(timezone.utc).date()}")
    print(f"Prompt version: {PROMPT_VERSION}")
    print(f"Endpoint: {args.url}")
    print(f"Cases: {len(cases)}")
    print("-" * 72)

    for case in cases:
        case_id = case["id"]
        label = case["label"]

        try:
            status, result = send_request(args.url, case["input"])
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            failures.append({
                "id": case_id,
                "label": label,
                "error": str(error),
            })
            print(f"FAIL {case_id} — {label}: request failed: {error}")
            continue

        if status != 200:
            failures.append({
                "id": case_id,
                "label": label,
                "error": f"HTTP {status}",
                "response": result,
            })
            print(f"FAIL {case_id} — {label}: HTTP {status}: {result}")
            continue

        if not isinstance(result, dict):
            failures.append({
                "id": case_id,
                "label": label,
                "error": "Expected a JSON object but received a different JSON type.",
                "response": result,
            })
            print(
                f"FAIL {case_id} — {label}: expected a JSON object, "
                f"received {type(result).__name__}: {result!r}"
            )
            continue

        actual_category = result.get("category")
        expected_category = case["expected_category"]
        category_evaluated += 1
        category_match = actual_category == expected_category

        if category_match:
            category_correct += 1
            category_status = "PASS"
        else:
            category_status = "FAIL"
            failures.append({
                "id": case_id,
                "label": label,
                "expected_category": expected_category,
                "actual_category": actual_category,
            })

        actual_flags = result.get("quality_flags")
        expected_flags = case["expected_flags"]
        flags_match = (
            isinstance(actual_flags, list)
            and set(actual_flags) == set(expected_flags)
        )
        flag_evaluated += 1

        if flags_match:
            flag_exact_matches += 1

        print(
            f"{category_status} {case_id} — {label}: "
            f"expected={expected_category}, actual={actual_category}; "
            f"flags_match={flags_match}"
        )

        if not category_match:
            print(f"  Response: {json.dumps(result, ensure_ascii=False)}")
        elif not flags_match:
            print(
                f"  Expected flags: {expected_flags}; "
                f"actual flags: {actual_flags}"
            )

    print("-" * 72)

    if category_evaluated:
        accuracy = 100 * category_correct / category_evaluated
        print(
            f"Category accuracy: {category_correct}/{category_evaluated} "
            f"({accuracy:.1f}%)"
        )
    else:
        print("Category accuracy: unavailable; no valid responses.")
        accuracy = 0.0

    if flag_evaluated:
        flag_accuracy = 100 * flag_exact_matches / flag_evaluated
        print(
            f"Exact quality-flag match: {flag_exact_matches}/{flag_evaluated} "
            f"({flag_accuracy:.1f}%)"
        )

    print(f"Failures: {len(failures)}")
    if failures:
        print(json.dumps(failures, indent=2, ensure_ascii=False))

    print("Note: category accuracy is the primary score; flag matches are reported separately.")
    print("Note: this is an eight-case evaluation, not a guarantee of production accuracy.")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
