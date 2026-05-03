"""AWS Bedrock plan generator — Claude Sonnet 4.6, Flex tier.

Produces a structured weekly plan: analysis (gaps), daily tasks, metrics, risks.
Plan is constrained by project context + this-week inputs (no random tasks).
"""
from typing import List, Dict, Any
import json
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

MODEL_ID = "anthropic.claude-sonnet-4-6-20250514-v1:0"
MAX_TOKENS = 3000

_client = None


def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return _client


SYSTEM = """You are an execution strategist for early-stage software teams.
Your job:
1. Read project context + this week's inputs
2. Identify the highest-impact gaps preventing progress
3. Convert gaps into concrete daily tasks (Mon-Fri) for the developer
4. Add handoff tasks for collaborators (artist review, QA) where needed
5. Define measurable success metrics tied to tasks
6. Flag risks with mitigation

Rules:
- Focus only on THIS WEEK execution
- Prefer fewer high-impact tasks over many low-value ones
- Each developer task: 2-8 hours, completable in one day
- Tasks must be specific and action-oriented (start with a verb)
- Avoid vague work ("improve X", "optimize Y") — name the specific thing
- Total developer effort must not exceed time_available_hours
- Spread tasks across Mon-Fri (day_index 0-4); leave Friday lighter for review
- Handoff tasks (is_handoff: true) go to artist/QA, do NOT count toward dev hours but should be scheduled
- Tie each task to a key gap or named outcome
- Include validation/measurement steps
- Output ONLY valid JSON, no markdown fences, no commentary"""


def _build_user_prompt(
    project: Dict[str, Any],
    weekly: Dict[str, Any],
    devs: List[str],
    previous: Dict[str, Any],
) -> str:
    return f"""Plan this developer's sprint week.

[PROJECT CONTEXT]
{json.dumps(project, indent=2)}

[CURRENT STATUS / THIS WEEK]
{json.dumps(weekly, indent=2)}

[TEAM]
Available people for handoffs / review: {", ".join(devs) if devs else "(developer only)"}

[PREVIOUS WEEK]
{json.dumps(previous, indent=2)}

Now produce the plan. Return ONLY this JSON:

{{
  "analysis": {{
    "current_stage_summary": "1-2 sentence read of where the project stands",
    "key_gaps": [
      {{"gap": "...", "impact": "high|medium|low", "reason": "..."}}
    ]
  }},
  "plan": {{
    "total_effort_hours": 0,
    "feasible": true,
    "tasks": [
      {{
        "title": "verb-first concrete task",
        "description": "1 sentence",
        "effort_hours": 4,
        "priority": "high|medium|low",
        "day_index": 0,
        "depends_on": ["other task title"],
        "expected_outcome": "what success looks like",
        "is_handoff": false,
        "assignee_name": "Developer Name or null"
      }}
    ]
  }},
  "metrics": [
    {{ "metric": "Plan generation time", "target": "< 10s", "linked_tasks": ["task title"] }}
  ],
  "risks": [
    {{ "risk": "...", "mitigation": "..." }}
  ]
}}"""


def generate_rich_plan(
    project: Dict[str, Any],
    weekly: Dict[str, Any],
    devs: List[Any],
    previous: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    dev_names = [d.name for d in devs] if devs else []
    dev_map = {d.name: d.id for d in devs} if devs else {}
    user_prompt = _build_user_prompt(project, weekly, dev_names, previous or {})

    try:
        response = _bedrock().invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            performanceConfigLatency="optimized",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM,
                "messages": [{"role": "user", "content": user_prompt}],
            }),
        )
        raw = json.loads(response["body"].read())
        text = raw["content"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
    except (ClientError, KeyError, json.JSONDecodeError, IndexError) as e:
        logger.error("Bedrock rich-plan error: %s", e)
        return _fallback(weekly)

    return _normalize(data, dev_map)


def _normalize(data: Dict[str, Any], dev_map: Dict[str, int]) -> Dict[str, Any]:
    analysis = data.get("analysis", {}) or {}
    plan = data.get("plan", {}) or {}
    tasks_raw = plan.get("tasks", []) or []

    tasks = []
    for t in tasks_raw:
        name = t.get("assignee_name")
        assignee_id = dev_map.get(name) if name and name != "null" else None
        di = t.get("day_index")
        try:
            di = int(di) if di is not None else None
            if di is not None and (di < 0 or di > 6):
                di = None
        except (ValueError, TypeError):
            di = None
        tasks.append({
            "title": str(t.get("title", "Task"))[:255],
            "description": str(t.get("description", ""))[:500],
            "effort_hours": max(1, min(12, int(t.get("effort_hours", 4) or 4))),
            "priority": t.get("priority") if t.get("priority") in ("high", "medium", "low") else "medium",
            "day_index": di,
            "depends_on": [str(x)[:255] for x in (t.get("depends_on") or []) if x][:5],
            "expected_outcome": str(t.get("expected_outcome", ""))[:300],
            "is_handoff": bool(t.get("is_handoff", False)),
            "assignee_id": assignee_id,
        })

    metrics = []
    for m in data.get("metrics", []) or []:
        if not m.get("metric"):
            continue
        metrics.append({
            "name": str(m["metric"])[:255],
            "target": str(m.get("target", ""))[:255],
            "linked_task_titles": [str(x)[:255] for x in (m.get("linked_tasks") or [])][:5],
        })

    risks = []
    for r in data.get("risks", []) or []:
        if not r.get("risk"):
            continue
        risks.append({
            "risk": str(r["risk"])[:500],
            "mitigation": str(r.get("mitigation", ""))[:500],
        })

    return {
        "analysis_summary": str(analysis.get("current_stage_summary", ""))[:500],
        "key_gaps": [
            {
                "gap": str(g.get("gap", ""))[:300],
                "impact": g.get("impact") if g.get("impact") in ("high", "medium", "low") else "medium",
                "reason": str(g.get("reason", ""))[:300],
            }
            for g in (analysis.get("key_gaps") or [])[:5]
        ],
        "tasks": tasks[:14],
        "metrics": metrics[:6],
        "risks": risks[:5],
        "raw": data,
    }


def _fallback(weekly: Dict[str, Any]) -> Dict[str, Any]:
    goal = weekly.get("goal", "")
    return {
        "analysis_summary": "Bedrock unavailable — minimal fallback plan.",
        "key_gaps": [],
        "tasks": [
            {
                "title": "Define this week's first concrete output",
                "description": f"From goal: {goal[:120]}",
                "effort_hours": 4, "priority": "high", "day_index": 0,
                "depends_on": [], "expected_outcome": "Clear scope for Tuesday work",
                "is_handoff": False, "assignee_id": None,
            },
            {
                "title": "Implement primary task",
                "description": "", "effort_hours": 6, "priority": "high",
                "day_index": 1, "depends_on": ["Define this week's first concrete output"],
                "expected_outcome": "", "is_handoff": False, "assignee_id": None,
            },
        ],
        "metrics": [],
        "risks": [{"risk": "LLM unavailable", "mitigation": "Retry generate; check Bedrock IAM"}],
        "raw": {"source": "fallback"},
    }
