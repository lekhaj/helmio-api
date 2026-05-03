from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db
from app.services.plan_generator import generate_rich_plan

router = APIRouter(prefix="/weekly-plans", tags=["weekly-plans"])


@router.get("/{plan_id}", response_model=schemas.WeeklyPlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(models.WeeklyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    return plan


@router.patch("/{plan_id}", response_model=schemas.WeeklyPlanOut)
def update_plan(plan_id: int, body: schemas.WeeklyPlanUpdate, db: Session = Depends(get_db)):
    plan = db.get(models.WeeklyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(models.WeeklyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    db.delete(plan)
    db.commit()


@router.post("/{plan_id}/generate", response_model=schemas.WeeklyPlanOut)
def generate_plan(plan_id: int, body: schemas.WeeklyPlanGenerate, db: Session = Depends(get_db)):
    plan = db.get(models.WeeklyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    project = db.get(models.Project, plan.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # persist any new this-week inputs
    if body.prompt is not None:
        plan.prompt = body.prompt
    if body.goal is not None:
        plan.goal = body.goal
    if body.context is not None:
        plan.context = body.context
    if body.time_available_hours is not None:
        plan.time_available_hours = body.time_available_hours
    if body.blockers is not None:
        plan.blockers = body.blockers
    if body.focus_areas is not None:
        plan.focus_areas = body.focus_areas

    # find previous week's plan for continuity
    prev = (
        db.query(models.WeeklyPlan)
        .filter(
            models.WeeklyPlan.project_id == plan.project_id,
            models.WeeklyPlan.id != plan.id,
            models.WeeklyPlan.week_start_date < plan.week_start_date,
        )
        .order_by(models.WeeklyPlan.week_start_date.desc())
        .first()
    )
    previous = {"goal": "", "completed_titles": [], "incomplete_titles": []}
    if prev:
        previous["goal"] = prev.goal or ""
        for t in prev.plan_tasks:
            (previous["completed_titles"] if t.status == models.PlanTaskStatus.done
             else previous["incomplete_titles"]).append(t.title)

    project_ctx = {
        "name": project.name,
        "vision": project.vision,
        "target_user": project.target_user,
        "stage": project.stage.value if project.stage else "mvp",
        "what_exists": project.what_exists or [],
        "problems": project.problems or [],
        "constraints": project.constraints or [],
    }
    weekly_ctx = {
        "goal": plan.goal,
        "context": plan.context,
        "research_prompt": plan.prompt,
        "time_available_hours": plan.time_available_hours,
        "blockers": plan.blockers or [],
        "focus_areas": plan.focus_areas or [],
    }

    devs = db.query(models.Developer).all()
    result = generate_rich_plan(project_ctx, weekly_ctx, devs, previous)

    # wipe previous tasks/metrics/risks
    db.query(models.PlanTask).filter(models.PlanTask.weekly_plan_id == plan_id).delete()
    db.query(models.WeeklyMetric).filter(models.WeeklyMetric.weekly_plan_id == plan_id).delete()
    db.query(models.WeeklyRisk).filter(models.WeeklyRisk.weekly_plan_id == plan_id).delete()

    plan.analysis_summary = result.get("analysis_summary", "")
    plan.key_gaps = result.get("key_gaps", [])
    plan.llm_response_raw = {
        "source": "bedrock",
        "model": "claude-sonnet-4-6",
        "task_count": len(result.get("tasks", [])),
    }
    plan.status = models.PlanStatus.active

    for idx, t in enumerate(result.get("tasks", [])):
        db.add(models.PlanTask(
            weekly_plan_id=plan_id,
            title=t["title"],
            description=t.get("description", ""),
            assignee_id=t.get("assignee_id"),
            effort_hours=t.get("effort_hours", 4),
            priority=models.Priority(t.get("priority", "medium")),
            order_index=idx,
            day_index=t.get("day_index"),
            expected_outcome=t.get("expected_outcome", ""),
            depends_on=t.get("depends_on", []),
            is_handoff=t.get("is_handoff", False),
        ))

    for m in result.get("metrics", []):
        db.add(models.WeeklyMetric(
            weekly_plan_id=plan_id,
            name=m["name"],
            target=m.get("target", ""),
            linked_task_titles=m.get("linked_task_titles", []),
        ))

    for r in result.get("risks", []):
        db.add(models.WeeklyRisk(
            weekly_plan_id=plan_id,
            risk=r["risk"],
            mitigation=r.get("mitigation", ""),
        ))

    db.commit()
    db.refresh(plan)
    return plan


# --- plan tasks under a plan ---

@router.post(
    "/{plan_id}/tasks", response_model=schemas.PlanTaskOut, status_code=status.HTTP_201_CREATED
)
def create_plan_task(
    plan_id: int, body: schemas.PlanTaskCreate, db: Session = Depends(get_db)
):
    if not db.get(models.WeeklyPlan, plan_id):
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    pt = models.PlanTask(weekly_plan_id=plan_id, **body.model_dump())
    db.add(pt)
    db.commit()
    db.refresh(pt)
    return pt
