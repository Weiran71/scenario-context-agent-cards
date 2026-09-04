from __future__ import annotations

import json
from pathlib import Path

try:
    from .engine import generate_cases
except ImportError:  # direct execution: python3 pipeline/run_examples.py
    from engine import generate_cases


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "public_cases.jsonl"
OUTPUT = ROOT / "examples" / "generated_outputs.jsonl"


def main() -> None:
    cases = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    outputs = generate_cases(cases)
    OUTPUT.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in outputs) + "\n", encoding="utf-8")
    counts = {}
    for item in outputs:
        key = (item["card_type"], item["decision"])
        counts[key] = counts.get(key, 0) + 1
    print(f"generated={len(outputs)} output={OUTPUT}")
    for (card_type, decision), count in sorted(counts.items()):
        print(f"{card_type:5s} {decision:11s} {count}")


if __name__ == "__main__":
    main()
