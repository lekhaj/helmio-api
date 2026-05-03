"""Clarifier — given free-text from user, returns scoped multi-select chip questions.

The LLM is constrained to a fixed taxonomy of fields per kind (project_intake,
weekly_intake) so it cannot wander into random territory. It generates *option
chips tailored to the user's input*, not the question itself.
"""
from typing import List, Dict, Any
import json
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

MODEL_ID = "global.anthropic.claude-sonnet-4-6"  # global inference profile = cheapest routing
MAX_TOKENS = 1200

_client = None


def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return _client


# ---- field taxonomies (the LLM must only ask about THESE) ----

PROJECT_FIELDS = [
    {
        "field": "stage",
        "question": "What stage is the product in?",
        "multi_select": False,
        "seed_options": ["Idea", "MVP", "Early users", "Growth", "Scaling"],
    },
    {
        "field": "what_exists",
        "question": "What's already built / working?",
        "multi_select": True,
        "seed_options": [],  # LLM tailors entirely to user description
    },
    {
        "field": "problems",
        "question": "What's broken or unblocked progress this week?",
        "multi_select": True,
        "seed_options": [],
    },
    {
        "field": "constraints",
        "question": "What constraints apply right now?",
        "multi_select": True,
        "seed_options": [
            "Solo developer", "Small team", "Limited time",
            "Budget-constrained", "GPU costs", "No integrations yet",
        ],
    },
    {
        "field": "target_user",
        "question": "Who is the primary user?",
        "multi_select": False,
        "seed_options": [],
    },
]

WEEKLY_FIELDS = [
    {
        "field": "focus_areas",
        "question": "Which parts of the product are in focus this week?",
        "multi_select": True,
        "seed_options": [],
    },
    {
        "field": "blockers",
        "question": "What's likely to slow you down?",
        "multi_select": True,
        "seed_options": [
            "Waiting on artist review", "Waiting on infra fix",
            "Prompt quality unclear", "Pipeline stage failing",
            "Manual testing overhead", "Cross-team handoff delays",
        ],
    },
    {
        "field": "time_available_hours",
        "question": "Realistic working hours this week?",
        "multi_select": False,
        "seed_options": ["20", "25", "30", "35", "40"],
    },
]


def _build_prompt(kind: str, user_text: str, known: Dict[str, Any], project_ctx: Dict[str, Any] | None) -> str:
    fields = PROJECT_FIELDS if kind == "project_intake" else WEEKLY_FIELDS
    field_block = json.dumps(fields, indent=2)
    known_block = json.dumps(known, indent=2) if known else "(none)"
    proj_block = json.dumps(project_ctx, indent=2) if project_ctx else "(no project context — this is project intake)"

    return f"""You generate clarifying multi-select chip questions for a sprint planner.
Your only goal is to fill the structured fields below. Do NOT invent fields.
Do NOT ask philosophical or generic questions. Tailor every option to what the user wrote.

Fields you may ask about (taxonomy — choose only fields that are NOT already populated in known_fields):
{field_block}

Project context (if relevant):
{proj_block}

Already-known fields (skip these):
{known_block}

User's free-text input:
\"\"\"{user_text}\"\"\"

For each field that still needs input, produce one question with 4-6 chip options that
this specific user is likely to pick from, derived from their input + any seed_options.
- For `what_exists` / `problems` / `focus_areas`: read the user's text carefully and
  extract concrete items (e.g. "FastAPI backend running", "Gradio UI", "TRELLIS pipeline").
- For `constraints` / `blockers`: combine seed_options with anything user mentioned.
- For `stage` / `target_user` / `time_available_hours`: use seed_options if user didn't say.
- Skip a field entirely if the user's text already clearly answers it (note in summary).
- Limit to 4 questions max per response. Pick the most important unfilled fields.

Output ONLY this JSON, no markdown:
{{
  "summary": "1-sentence acknowledgement of what you understood from the user's text",
  "questions": [
    {{
      "field": "stage",
      "question": "What stage is the product in?",
      "multi_select": false,
      "options": [
        {{ "label": "MVP", "value": "mvp" }},
        {{ "label": "Early users", "value": "early_users" }}
      ],
      "allow_custom": true
    }}
  ]
}}"""


def clarify(kind: str, user_text: str, known: Dict[str, Any], project_ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
    prompt = _build_prompt(kind, user_text, known, project_ctx)
    try:
        # Note: Flex tier (performanceConfigLatency=optimized) is not supported
        # for Sonnet 4.6 in us-east-1 — using standard latency. Cost levers we keep:
        # base model ID (global routing), tight max_tokens, single call.
        response = _bedrock().invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
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
        logger.error("Clarifier error: %s — falling back to seed questions", e)
        return _fallback(kind, known)

    # sanitize
    questions = []
    for q in data.get("questions", []):
        opts = []
        for o in q.get("options", []):
            if isinstance(o, dict) and o.get("label"):
                opts.append({"label": str(o["label"])[:80], "value": str(o.get("value", o["label"]))[:80]})
        if opts:
            questions.append({
                "field": q.get("field", "unknown"),
                "question": str(q.get("question", ""))[:200],
                "multi_select": bool(q.get("multi_select", True)),
                "options": opts[:8],
                "allow_custom": bool(q.get("allow_custom", True)),
            })
    return {"summary": str(data.get("summary", ""))[:300], "questions": questions[:4]}


def _fallback(kind: str, known: Dict[str, Any]) -> Dict[str, Any]:
    fields = PROJECT_FIELDS if kind == "project_intake" else WEEKLY_FIELDS
    out = []
    for f in fields:
        if f["field"] in known and known[f["field"]]:
            continue
        seeds = f["seed_options"] or ["Option 1", "Option 2", "Option 3"]
        out.append({
            "field": f["field"],
            "question": f["question"],
            "multi_select": f["multi_select"],
            "options": [{"label": s, "value": s.lower().replace(" ", "_")} for s in seeds],
            "allow_custom": True,
        })
        if len(out) >= 4:
            break
    return {"summary": "Bedrock unavailable — using fallback questions.", "questions": out}
