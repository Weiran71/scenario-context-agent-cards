from __future__ import annotations

import json
import sys
from pathlib import Path


# The public package must not contain proprietary brand names, private endpoints,
# or local machine paths. Concrete internal names are intentionally not embedded
# in the public checker.
FORBIDDEN = ("internal_brand_name", "private_endpoint", "/Users/")
REQUIRED = {"case_id", "card_type", "decision", "need_record", "decision_reasons"}
NEED_REQUIRED = {"situation", "need", "constraints", "evidence", "confidence"}


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
        need = item.get("need_record")
        if not isinstance(need, dict):
            errors.append(f"line {line_no}: need_record must be an object")
        else:
            missing_need = NEED_REQUIRED - need.keys()
            if missing_need:
                errors.append(f"line {line_no}: need_record missing {sorted(missing_need)}")
            confidence = need.get("confidence")
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                errors.append(f"line {line_no}: need_record confidence must be in [0, 1]")
        if item.get("decision") == "serve":
            card = item.get("card")
            if not isinstance(card, dict):
                errors.append(f"line {line_no}: served result must contain an object card")
            else:
                required_card = {"main_copy", "sub_copy", "action", "icon_tag"} if item.get("card_type") == "event" else {"theme", "main_copy", "sub_copy"}
                missing_card = required_card - card.keys()
                if missing_card:
                    errors.append(f"line {line_no}: card missing {sorted(missing_card)}")
                if item.get("card_type") == "event" and isinstance(card.get("icon_tag"), dict):
                    if {"en", "zh"} - card["icon_tag"].keys():
                        errors.append(f"line {line_no}: event icon_tag requires en and zh")
        if item.get("card_type") == "poi":
            pool = item.get("candidate_pool")
            selected = item.get("selected_pois")
            if not isinstance(pool, list) or not isinstance(selected, list):
                errors.append(f"line {line_no}: poi output requires candidate_pool and selected_pois arrays")
            elif len(selected) > 3:
                errors.append(f"line {line_no}: selected_pois must contain at most 3 items")
            elif any(not isinstance(p, dict) or not {"poi_id", "name"} <= p.keys() for p in selected):
                errors.append(f"line {line_no}: every selected_pois item requires poi_id and name")
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
