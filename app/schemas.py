from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, date
from app.models import (
    TaskStatus,
    ProjectStatus,
    PlanStatus,
    Priority,
    PlanTaskStatus,
)


# --- existing simple task tracker ---

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


# --- developers ---

class DeveloperBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = None


class DeveloperCreate(DeveloperBase):
    pass


class DeveloperOut(DeveloperBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# --- projects ---

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str = ""
    kpi_primary: Optional[str] = None
    kpi_secondary: Optional[str] = None
    color: str = "violet"


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=160)
    description: Optional[str] = None
    kpi_primary: Optional[str] = None
    kpi_secondary: Optional[str] = None
    color: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    kpi_primary: Optional[str]
    kpi_secondary: Optional[str]
    status: ProjectStatus
    color: str
    created_at: datetime
    updated_at: datetime
    weekly_plan_count: int = 0
    active_task_count: int = 0
    model_config = {"from_attributes": True}


# --- plan tasks ---

class PlanTaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    assignee_id: Optional[int] = None
    effort_hours: int = Field(4, ge=1, le=80)
    priority: Priority = Priority.medium
    status: PlanTaskStatus = PlanTaskStatus.todo
    order_index: int = 0


class PlanTaskCreate(PlanTaskBase):
    pass


class PlanTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    effort_hours: Optional[int] = Field(None, ge=1, le=80)
    priority: Optional[Priority] = None
    status: Optional[PlanTaskStatus] = None
    order_index: Optional[int] = None


class PlanTaskOut(PlanTaskBase):
    id: int
    weekly_plan_id: int
    assignee: Optional[DeveloperOut] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# --- weekly plans ---

class WeeklyPlanCreate(BaseModel):
    week_start_date: date
    goal: str = ""
    context: str = ""


class WeeklyPlanUpdate(BaseModel):
    goal: Optional[str] = None
    context: Optional[str] = None
    prompt: Optional[str] = None
    status: Optional[PlanStatus] = None


class WeeklyPlanGenerate(BaseModel):
    prompt: str = Field(..., min_length=1)
    goal: Optional[str] = None
    context: Optional[str] = None


class WeeklyPlanOut(BaseModel):
    id: int
    project_id: int
    week_start_date: date
    goal: str
    context: str
    prompt: str
    status: PlanStatus
    created_at: datetime
    updated_at: datetime
    plan_tasks: List[PlanTaskOut] = []
    model_config = {"from_attributes": True}
