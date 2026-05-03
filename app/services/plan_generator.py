"""Stub plan generator. Phase 2 will replace this with AWS Bedrock Sonnet 4.5."""
from typing import List, Dict, Any
import re


def _extract_themes(prompt: str, goal: str) -> List[str]:
    text = f"{goal}. {prompt}".lower()
    themes = []
    for kw, label in [
        (r"\b(auth|login|signup)\b", "Authentication"),
        (r"\b(dashboard|metrics|analytics)\b", "Analytics dashboard"),
        (r"\b(api|endpoint|backend)\b", "API"),
        (r"\b(ui|design|frontend|web)\b", "Frontend"),
        (r"\b(test|qa|coverage)\b", "Testing"),
        (r"\b(deploy|ci|cd|infra)\b", "Deployment"),
        (r"\b(bug|fix|issue)\b", "Bug fixes"),
        (r"\b(perf|performance|speed|latency)\b", "Performance"),
        (r"\b(doc|documentation)\b", "Documentation"),
    ]:
        if re.search(kw, text):
            themes.append(label)
    if not themes:
        themes = ["Discovery", "Implementation", "Validation"]
    return themes[:5]


def generate_stub_tasks(
    prompt: str, goal: str, devs: List[Any]
) -> List[Dict[str, Any]]:
    """Return a believable set of weekly tasks derived from the prompt themes."""
    themes = _extract_themes(prompt, goal)
    dev_ids = [d.id for d in devs] if devs else [None]

    base_efforts = [6, 4, 8, 4, 6, 3, 5, 4]
    base_priorities = ["high", "medium", "high", "low", "medium", "medium", "low", "medium"]

    tasks: List[Dict[str, Any]] = []
    counter = 0
    for theme in themes:
        # 2 tasks per theme
        sub_titles = [
            f"Scope and design — {theme}",
            f"Implement — {theme}",
        ]
        for sub in sub_titles:
            tasks.append(
                {
                    "title": sub,
                    "description": f"Auto-generated from goal: {goal[:120]}" if goal else "",
                    "assignee_id": dev_ids[counter % len(dev_ids)] if dev_ids[0] else None,
                    "effort_hours": base_efforts[counter % len(base_efforts)],
                    "priority": base_priorities[counter % len(base_priorities)],
                }
            )
            counter += 1
    return tasks[:8]
