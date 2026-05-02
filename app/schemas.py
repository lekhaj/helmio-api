from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models import TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    status: TaskStatus = TaskStatus.todo


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeedbackCreate(BaseModel):
    task_id: Optional[int] = None
    content: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5)


class FeedbackOut(BaseModel):
    id: int
    task_id: Optional[int]
    content: str
    rating: int
    created_at: datetime

    model_config = {"from_attributes": True}
