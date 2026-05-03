from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


def _decorate(project: models.Project, db: Session) -> schemas.ProjectOut:
    plan_count = (
        db.query(func.count(models.WeeklyPlan.id))
        .filter(models.WeeklyPlan.project_id == project.id)
        .scalar()
    )
    active_tasks = (
        db.query(func.count(models.PlanTask.id))
        .join(models.WeeklyPlan, models.WeeklyPlan.id == models.PlanTask.weekly_plan_id)
        .filter(
            models.WeeklyPlan.project_id == project.id,
            models.PlanTask.status != models.PlanTaskStatus.done,
        )
        .scalar()
    )
    out = schemas.ProjectOut.model_validate(project)
    out.weekly_plan_count = plan_count or 0
    out.active_task_count = active_tasks or 0
    return out


@router.get("/", response_model=List[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.updated_at.desc()).all()
    return [_decorate(p, db) for p in projects]


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _decorate(project, db)


@router.post("/", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: schemas.ProjectCreate, db: Session = Depends(get_db)):
    project = models.Project(**body.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return _decorate(project, db)


@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def update_project(project_id: int, body: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _decorate(project, db)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()


# --- weekly plans nested under projects ---

@router.get("/{project_id}/weekly-plans", response_model=List[schemas.WeeklyPlanOut])
def list_project_plans(project_id: int, db: Session = Depends(get_db)):
    if not db.get(models.Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(models.WeeklyPlan)
        .filter(models.WeeklyPlan.project_id == project_id)
        .order_by(models.WeeklyPlan.week_start_date.desc())
        .all()
    )


@router.post(
    "/{project_id}/weekly-plans",
    response_model=schemas.WeeklyPlanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_project_plan(
    project_id: int, body: schemas.WeeklyPlanCreate, db: Session = Depends(get_db)
):
    if not db.get(models.Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    plan = models.WeeklyPlan(project_id=project_id, **body.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
