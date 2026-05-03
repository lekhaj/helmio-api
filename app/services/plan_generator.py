"""AWS Bedrock plan generator — Claude Sonnet 4.6, Flex tier."""
from typing import List, Dict, Any
import json
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

MODEL_ID = "anthropic.claude-sonnet-4-6-20250514-v1:0"
MAX_TOKENS = 1024

_client = None


def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return _client


def _build_prompt(prompt: str, goal: str, context: str, dev_names: List[str]) -> str:
    devs_str = ", ".join(dev_names) if dev_names else "unassigned"
    return f"""You are a senior engineering manager helping plan a software sprint.

Project goal this week: {goal or "Not specified"}
Additional context: {context or "None"}
Research prompt from user: {prompt}
Available team members: {devs_str}

Generate a realistic, actionable weekly task list for this sprint.
Rules:
- Between 6 and 10 tasks
- Total effort_hours must not exceed 40h
- Each task effort_hours between 1 and 8
- Assign tasks evenly across team members (use exact names from the list, or null for unassigned)
- Priority: "high", "medium", or "low"
- Titles should be concrete and action-oriented (start with a verb)

Respond ONLY with a JSON array — no markdown, no explanation, nothing else:
[
  {{
    "title": "string",
    "description": "one-sentence description",
    "effort_hours": 4,
    "priority": "medium",
    "assignee_name": "Developer Name or null"
  }}
]"""


def generate_plan_tasks(
    prompt: str,
    goal: str,
    context: str,
    devs: List[Any],
) -> List[Dict[str, Any]]:
    dev_names = [d.name for d in devs] if devs else []
    dev_map = {d.name: d.id for d in devs} if devs else {}

    user_prompt = _build_prompt(prompt, goal, context, dev_names)

    try:
        response = _bedrock().invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            performanceConfigLatency="optimized",  # Flex tier — cheaper, async-safe
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": user_prompt}],
            }),
        )
        raw = json.loads(response["body"].read())
        text = raw["content"][0]["text"].strip()

        # strip accidental markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        tasks_raw = json.loads(text)

    except ClientError as e:
        logger.error("Bedrock ClientError: %s", e)
        return _fallback(prompt, goal, devs)
    except (KeyError, json.JSONDecodeError, IndexError) as e:
        logger.error("Bedrock parse error: %s", e)
        return _fallback(prompt, goal, devs)

    tasks: List[Dict[str, Any]] = []
    for t in tasks_raw:
        name = t.get("assignee_name")
        assignee_id = dev_map.get(name) if name and name != "null" else None
        tasks.append({
            "title": str(t.get("title", "Task"))[:255],
            "description": str(t.get("description", ""))[:500],
            "effort_hours": max(1, min(8, int(t.get("effort_hours", 4)))),
            "priority": t.get("priority", "medium") if t.get("priority") in ("high", "medium", "low") else "medium",
            "assignee_id": assignee_id,
        })
    return tasks[:10]


def _fallback(prompt: str, goal: str, devs: List[Any]) -> List[Dict[str, Any]]:
    """Minimal fallback used only when Bedrock is unreachable."""
    import re
    text = f"{goal}. {prompt}".lower()
    themes = []
    for kw, label in [
        (r"\b(auth|login|signup)\b", "Authentication"),
        (r"\b(dashboard|metrics|analytics)\b", "Analytics dashboard"),
        (r"\b(api|endpoint|backend)\b", "API"),
        (r"\b(ui|design|frontend)\b", "Frontend"),
        (r"\b(test|qa)\b", "Testing"),
        (r"\b(deploy|infra)\b", "Deployment"),
    ]:
        if re.search(kw, text):
            themes.append(label)
    if not themes:
        themes = ["Discovery", "Implementation", "Validation"]

    dev_ids = [d.id for d in devs] if devs else [None]
    tasks, i = [], 0
    for theme in themes[:4]:
        for verb in ("Design", "Implement"):
            tasks.append({
                "title": f"{verb} — {theme}",
                "description": "",
                "effort_hours": [4, 6][i % 2],
                "priority": ["high", "medium"][i % 2],
                "assignee_id": dev_ids[i % len(dev_ids)] if dev_ids[0] else None,
            })
            i += 1
    return tasks[:8]
