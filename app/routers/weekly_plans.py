from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db
from app.services.plan_generator import generate_stub_tasks

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
    """Stub: returns mock generated tasks. Replaced by Bedrock in Phase 2."""
    plan = db.get(models.WeeklyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")

    plan.prompt = body.prompt
    if body.goal is not None:
        plan.goal = body.goal
    if body.context is not None:
        plan.context = body.context

    # clear existing tasks
    db.query(models.PlanTask).filter(models.PlanTask.weekly_plan_id == plan_id).delete()

    devs = db.query(models.Developer).all()
    generated = generate_stub_tasks(prompt=body.prompt, goal=plan.goal or "", devs=devs)

    for idx, t in enumerate(generated):
        db.add(
            models.PlanTask(
                weekly_plan_id=plan_id,
                title=t["title"],
                description=t.get("description", ""),
                assignee_id=t.get("assignee_id"),
                effort_hours=t.get("effort_hours", 4),
                priority=models.Priority(t.get("priority", "medium")),
                order_index=idx,
            )
        )

    plan.llm_response_raw = {"source": "stub", "task_count": len(generated)}
    plan.status = models.PlanStatus.active
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
