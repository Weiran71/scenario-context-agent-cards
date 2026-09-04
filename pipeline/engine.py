"""A deterministic, dependency-free baseline for the public Context2Card project.

The implementation intentionally uses transparent rules instead of any proprietary
service. It demonstrates the public contract; it is not a production recommender.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


@dataclass
class NeedRecord:
    situation: str
    need: str
    constraints: List[str]
    evidence: List[str]
    confidence: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "situation": self.situation,
            "need": self.need,
            "constraints": self.constraints,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
        }


def _time_label(hour: int) -> str:
    if hour < 6:
        return "清晨"
    if hour < 11:
        return "上午"
    if hour < 14:
        return "午间"
    if hour < 18:
        return "下午"
    if hour < 22:
        return "晚间"
    return "深夜"


def build_need_record(context: Dict[str, Any], card_type: str) -> NeedRecord:
    """Translate context into a bounded, auditable situation hypothesis."""
    user = context.get("user", {})
    env = context.get("environment", {})
    hour = int(env.get("local_hour", 12))
    period = _time_label(hour)
    weather = env.get("weather", "晴朗")
    local_status = user.get("local_status", "local")
    relation = "常驻城市" if local_status == "local" else "到访城市"
    prefs = list(user.get("preference_tags", []))
    evidence = [f"时间处于{period}", f"当前天气为{weather}", f"用户属于{relation}"]

    constraints = ["事实必须在当前时间有效", "不使用未提供的行程或订单信息"]
    if weather in {"暴雨", "大雪", "大风"}:
        constraints.append("优先室内或低暴露活动")
    else:
        constraints.append("优先当前可达且距离合理的内容")

    if card_type == "event":
        event = context.get("event", {})
        event_theme = event.get("theme", "日常活动")
        need = f"判断{event_theme}是否值得在当前时机提醒"
        situation = f"{period}，用户位于{env.get('district', '示例城区')}，面对一个{event_theme}事件"
        evidence.append(f"事件状态为{event.get('status', 'unknown')}")
        confidence = 0.85 if event.get("status") == "active" else 0.45
    else:
        need = "寻找与当前时间、距离和用户偏好匹配的低决策成本去处"
        situation = f"{period}，用户位于{env.get('district', '示例城区')}，需要附近可去的地点"
        if prefs:
            evidence.append("用户偏好：" + "、".join(prefs))
        confidence = 0.8 if prefs else 0.6

    return NeedRecord(situation, need, constraints, evidence, confidence)


def _event_decision(context: Dict[str, Any], need: NeedRecord) -> Tuple[str, List[str]]:
    event = context.get("event", {})
    reasons: List[str] = []
    if event.get("status") != "active":
        reasons.append("事件不是当前有效状态")
    distance = float(event.get("distance_km", 99))
    if distance > 8:
        reasons.append("事件距离超过公开版可达范围")
    if float(event.get("relevance", 0)) < 0.6:
        reasons.append("事件与当前用户关系不足")
    if reasons:
        return "stay_silent", reasons
    reasons.extend(["事件在当前时间有效", "距离和用户关系满足提醒条件"])
    return "serve", reasons


def generate_event_card(context: Dict[str, Any]) -> Dict[str, Any]:
    need = build_need_record(context, "event")
    decision, reasons = _event_decision(context, need)
    event = context.get("event", {})
    if decision == "stay_silent":
        card = None
    else:
        theme = event.get("theme", "附近活动")
        card = {
            "main_copy": f"{theme}正适合现在去看看",
            "sub_copy": event.get("fact_line", "就在附近，时间合适")[:30],
            "action": event.get("action", "查看详情"),
            "icon_tag": event.get("icon_tag", {"en": "activity", "zh": "活动"}),
        }
    return {
        "card_type": "event",
        "decision": decision,
        "need_record": need.as_dict(),
        "card": card,
        "decision_reasons": reasons,
        "source": "synthetic",
    }


def _poi_score(poi: Dict[str, Any], context: Dict[str, Any]) -> Tuple[float, List[str]]:
    user_tags = set(context.get("user", {}).get("preference_tags", []))
    poi_tags = set(poi.get("tags", []))
    overlap = len(user_tags & poi_tags)
    distance = float(poi.get("distance_km", 99))
    if distance > 5 or poi.get("status") != "open":
        return -1.0, ["不满足距离或当前可用性条件"]
    summary_match = 1 if poi.get("summary_theme") in poi_tags or poi.get("summary_theme") in user_tags else 0
    score = max(0.0, 1.0 - distance / 6.0) * 0.45 + min(overlap, 3) / 3.0 * 0.35 + summary_match * 0.2
    reasons = [f"距离{distance:g}公里"]
    if overlap:
        reasons.append("命中用户偏好：" + "、".join(sorted(user_tags & poi_tags)))
    if summary_match:
        reasons.append("Summary 主题与当前偏好一致")
    return score, reasons


def generate_poi_card(context: Dict[str, Any]) -> Dict[str, Any]:
    need = build_need_record(context, "poi")
    scored: List[Tuple[float, Dict[str, Any], List[str]]] = []
    for poi in context.get("poi_candidates", []):
        score, reasons = _poi_score(poi, context)
        if score >= 0:
            scored.append((score, poi, reasons))
    scored.sort(key=lambda item: (-item[0], float(item[1].get("distance_km", 99))))
    selected = scored[:3]
    if not selected or selected[0][0] < 0.42:
        return {
            "card_type": "poi",
            "decision": "stay_silent",
            "need_record": need.as_dict(),
            "candidate_pool": [p.get("poi_id") for p in context.get("poi_candidates", [])],
            "selected_pois": [],
            "card": None,
            "decision_reasons": ["没有候选地点同时满足距离、可用性和关系条件"],
            "source": "synthetic",
        }
    pois = [item[1] for item in selected]
    farthest = max(float(p.get("distance_km", 0)) for p in pois)
    theme = pois[0].get("theme", "附近去处")
    return {
        "card_type": "poi",
        "decision": "serve",
        "need_record": need.as_dict(),
        "candidate_pool": [p.get("poi_id") for p in context.get("poi_candidates", [])],
        "selected_pois": [{"poi_id": p.get("poi_id"), "name": p.get("name")} for p in pois],
        "card": {
            "theme": theme,
            "main_copy": f"{theme}就在附近，去走走吧",
            "sub_copy": f"{farthest:g}公里内有{len(pois)}个合适去处",
        },
        "decision_reasons": [reason for _, _, rs in selected for reason in rs],
        "source": "synthetic",
    }


def generate_case(case: Dict[str, Any]) -> Dict[str, Any]:
    card_type = case.get("card_type")
    context = case.get("context", {})
    result = generate_event_card(context) if card_type == "event" else generate_poi_card(context)
    result["case_id"] = case.get("case_id")
    result["expected_decision"] = case.get("expected_decision")
    return result


def generate_cases(cases: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [generate_case(case) for case in cases]

