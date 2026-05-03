from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/plan-tasks", tags=["plan-tasks"])


@router.patch("/{task_id}", response_model=schemas.PlanTaskOut)
def update_plan_task(
    task_id: int, body: schemas.PlanTaskUpdate, db: Session = Depends(get_db)
):
    task = db.get(models.PlanTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Plan task not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.PlanTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Plan task not found")
    db.delete(task)
    db.commit()
