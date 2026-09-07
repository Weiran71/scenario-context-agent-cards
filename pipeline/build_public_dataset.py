"""Build the public synthetic dataset used by the GitHub and HF artifacts."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from .engine import generate_case
except ImportError:  # direct execution: python3 pipeline/build_public_dataset.py
    from engine import generate_case


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
HF_DIR = ROOT / "hf_dataset"


def event_case(index: int, positive: bool) -> dict:
    themes = ["周末市集", "亲子手作", "户外音乐会", "城市展览", "夜间灯会"]
    theme = themes[index % len(themes)]
    districts = ["星河城区", "云杉城区", "南湖城区", "石桥城区"]
    district = districts[index % len(districts)]
    if positive:
        event = {
            "theme": theme,
            "status": "active",
            "distance_km": [1.3, 2.1, 3.6, 4.4, 5.2][index % 5],
            "relevance": [0.72, 0.79, 0.84, 0.9, 0.68][index % 5],
            "fact_line": f"今天{10 + index}:00-18:00，{district}有{theme}",
            "action": ["去看看", "去参加", "去听听"][index % 3],
            "icon_tag": {"en": ["market", "family", "music", "exhibition", "festival"][index % 5], "zh": ["市集", "亲子", "音乐", "展览", "节庆"][index % 5]},
        }
        expected = "serve"
    else:
        failure = index % 3
        event = {
            "theme": theme,
            "status": "expired" if failure == 0 else "active",
            "distance_km": 18.0 if failure == 1 else 1.5,
            "relevance": 0.35 if failure == 2 else 0.86,
            "fact_line": "公开示例事件不满足当前服务条件",
            "action": "去看看",
            "icon_tag": {"en": "activity", "zh": "活动"},
        }
        expected = "stay_silent"
    return {
        "case_id": f"event_{'positive' if positive else 'negative'}_{index:02d}",
        "card_type": "event",
        "expected_decision": expected,
        "context": {
            "user": {
                "local_status": "local" if index % 2 == 0 else "visitor",
                "preference_tags": [["户外", "轻松活动"], ["亲子", "室内"], ["音乐", "夜间活动"], ["文化", "安静"]][index % 4],
            },
            "environment": {
                "district": district,
                "local_hour": [9, 11, 15, 19, 20][index % 5],
                "weather": ["晴朗", "小雨", "阴天", "晴朗", "微风"][index % 5],
            },
            "event": event,
        },
    }


def poi_case(index: int, positive: bool) -> dict:
    themes = ["散步去处", "亲子去处", "安静去处", "晨间运动", "室内去处"]
    theme = themes[index % len(themes)]
    tags = [["户外", "散步"], ["亲子", "室内"], ["咖啡", "安静"], ["运动", "户外"], ["室内", "阅读"]][index % 5]
    user_tags = tags[:]
    if positive:
        distances = [0.9, 1.4, 2.0, 2.8, 3.5]
        candidates = []
        for rank in range(3):
            candidates.append(
                {
                    "poi_id": f"poi_demo_{index:02d}{rank + 1}",
                    "name": f"{theme}示例点{chr(65 + rank)}",
                    "distance_km": distances[(index + rank) % len(distances)],
                    "status": "open",
                    "tags": tags if rank < 2 else [tags[0]],
                    "summary_theme": tags[0] if rank < 2 else "休闲",
                    "theme": theme,
                }
            )
        expected = "serve"
    else:
        failure = index % 2
        candidates = [
            {
                "poi_id": f"poi_demo_{index:02d}1",
                "name": "不可用示例点A" if failure == 0 else "过远示例点A",
                "distance_km": 1.2 if failure == 0 else 12.0,
                "status": "closed" if failure == 0 else "open",
                "tags": tags,
                "summary_theme": tags[0],
                "theme": theme,
            },
            {
                "poi_id": f"poi_demo_{index:02d}2",
                "name": "不可用示例点B" if failure == 0 else "过远示例点B",
                "distance_km": 1.8 if failure == 0 else 15.0,
                "status": "closed" if failure == 0 else "open",
                "tags": tags,
                "summary_theme": tags[0],
                "theme": theme,
            },
        ]
        expected = "stay_silent"
    return {
        "case_id": f"poi_{'positive' if positive else 'negative'}_{index:02d}",
        "card_type": "poi",
        "expected_decision": expected,
        "context": {
            "user": {"local_status": "local" if index % 2 == 0 else "visitor", "preference_tags": user_tags},
            "environment": {
                "district": ["星河城区", "云杉城区", "南湖城区", "石桥城区"][index % 4],
                "local_hour": [7, 10, 13, 16, 19][index % 5],
                "weather": ["晴朗", "小雨", "阴天", "晴朗", "微风"][index % 5],
            },
            "poi_candidates": candidates,
        },
    }


def build() -> list[dict]:
    cases = []
    for positive in (True, False):
        cases.extend(event_case(i, positive) for i in range(10))
        cases.extend(poi_case(i, positive) for i in range(10))
    return cases


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def main() -> None:
    cases = build()
    write_jsonl(DATA_DIR / "public_cases.jsonl", cases)
    for config in ("event_positive", "event_negative", "poi_positive", "poi_negative"):
        prefix, polarity = config.split("_")
        rows = []
        for row in cases:
            if row["card_type"] != prefix or row["expected_decision"] != ("serve" if polarity == "positive" else "stay_silent"):
                continue
            generated = generate_case(row)
            rows.append({**row, "reference_output": generated})
        write_jsonl(HF_DIR / f"{config}.jsonl", rows)
    print(f"built {len(cases)} cases under {DATA_DIR} and {HF_DIR}")


if __name__ == "__main__":
    main()
