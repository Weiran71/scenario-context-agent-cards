from __future__ import annotations

import json
import sys
from pathlib import Path


# The public package must not contain proprietary brand names, private endpoints,
# or local machine paths. Concrete internal names are intentionally not embedded
# in the public checker.
FORBIDDEN = ("internal_brand_name", "private_endpoint", "/Users/")
REQUIRED = {"case_id", "card_type", "decision", "need_record", "decision_reasons"}


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON ({exc})")
            continue
        missing = REQUIRED - item.keys()
        if missing:
            errors.append(f"line {line_no}: missing {sorted(missing)}")
        case_id = item.get("case_id")
        if case_id in seen:
            errors.append(f"line {line_no}: duplicate case_id {case_id}")
        seen.add(case_id)
        if item.get("card_type") not in {"event", "poi"}:
            errors.append(f"line {line_no}: unsupported card_type")
        if item.get("decision") not in {"serve", "stay_silent"}:
            errors.append(f"line {line_no}: unsupported decision")
        if item.get("expected_decision") and item.get("expected_decision") != item.get("decision"):
            errors.append(
                f"line {line_no}: decision mismatch, expected={item.get('expected_decision')} actual={item.get('decision')}"
            )
        if item.get("decision") == "stay_silent" and item.get("card") is not None:
            errors.append(f"line {line_no}: silent result must not contain a card")
        text = json.dumps(item, ensure_ascii=False)
        for token in FORBIDDEN:
            if token in text:
                errors.append(f"line {line_no}: forbidden token {token}")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 validators/validate_outputs.py <jsonl>")
        return 2
    errors = validate(Path(sys.argv[1]))
    if errors:
        print("FAIL")
        print("\n".join(errors))
        return 1
    print("PASS: output structure and public-boundary checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
