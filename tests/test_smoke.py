from __future__ import annotations

import json
import unittest
from pathlib import Path

from pipeline.engine import generate_cases


class PublicPipelineSmokeTest(unittest.TestCase):
    def test_both_card_types_and_decisions(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cases = [json.loads(line) for line in (root / "data/public_cases.jsonl").read_text(encoding="utf-8").splitlines()]
        outputs = generate_cases(cases)
        self.assertEqual(len(outputs), 40)
        self.assertEqual({item["card_type"] for item in outputs}, {"event", "poi"})
        self.assertIn("serve", {item["decision"] for item in outputs})
        self.assertIn("stay_silent", {item["decision"] for item in outputs})
        self.assertEqual(sum(item["card_type"] == "event" and item["decision"] == "serve" for item in outputs), 10)
        self.assertEqual(sum(item["card_type"] == "event" and item["decision"] == "stay_silent" for item in outputs), 10)
        self.assertEqual(sum(item["card_type"] == "poi" and item["decision"] == "serve" for item in outputs), 10)
        self.assertEqual(sum(item["card_type"] == "poi" and item["decision"] == "stay_silent" for item in outputs), 10)
        for item in outputs:
            self.assertEqual(item["expected_decision"], item["decision"])

        hf_dir = root / "hf_dataset"
        for config in ("event_positive", "event_negative", "poi_positive", "poi_negative"):
            rows = [json.loads(line) for line in (hf_dir / f"{config}.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 10)
            self.assertTrue(all("reference_output" in row for row in rows))


if __name__ == "__main__":
    unittest.main()
