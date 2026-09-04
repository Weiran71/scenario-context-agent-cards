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
        self.assertGreaterEqual(len(outputs), 4)
        self.assertEqual({item["card_type"] for item in outputs}, {"event", "poi"})
        self.assertIn("serve", {item["decision"] for item in outputs})
        self.assertIn("stay_silent", {item["decision"] for item in outputs})
        for item in outputs:
            self.assertEqual(item["expected_decision"], item["decision"])


if __name__ == "__main__":
    unittest.main()

