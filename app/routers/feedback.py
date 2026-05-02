from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/", response_model=List[schemas.FeedbackOut])
def list_feedback(task_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(models.Feedback)
    if task_id is not None:
        q = q.filter(models.Feedback.task_id == task_id)
    return q.order_by(models.Feedback.created_at.desc()).all()


@router.post("/", response_model=schemas.FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(body: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    if body.task_id is not None and not db.get(models.Task, body.task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    fb = models.Feedback(**body.model_dump())
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: int, db: Session = Depends(get_db)):
    fb = db.get(models.Feedback, feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    db.delete(fb)
    db.commit()
