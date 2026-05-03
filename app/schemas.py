from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal, Any, Dict
from datetime import datetime, date
from app.models import (
    TaskStatus,
    ProjectStatus,
    ProjectStage,
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
    vision: str = ""
    target_user: str = ""
    stage: ProjectStage = ProjectStage.mvp
    constraints: List[str] = Field(default_factory=list)
    what_exists: List[str] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list)
    kpi_primary: Optional[str] = None
    kpi_secondary: Optional[str] = None
    color: str = "violet"


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=160)
    description: Optional[str] = None
    vision: Optional[str] = None
    target_user: Optional[str] = None
    stage: Optional[ProjectStage] = None
    constraints: Optional[List[str]] = None
    what_exists: Optional[List[str]] = None
    problems: Optional[List[str]] = None
    kpi_primary: Optional[str] = None
    kpi_secondary: Optional[str] = None
    color: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    vision: str
    target_user: str
    stage: ProjectStage
    constraints: List[str]
    what_exists: List[str]
    problems: List[str]
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
    day_index: Optional[int] = Field(None, ge=0, le=6)
    expected_outcome: str = ""
    depends_on: List[str] = Field(default_factory=list)
    is_handoff: bool = False


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
    day_index: Optional[int] = Field(None, ge=0, le=6)
    expected_outcome: Optional[str] = None
    is_handoff: Optional[bool] = None


class PlanTaskOut(PlanTaskBase):
    id: int
    weekly_plan_id: int
    assignee: Optional[DeveloperOut] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# --- weekly plans ---

class WeeklyMetricOut(BaseModel):
    id: int
    name: str
    target: str
    linked_task_titles: List[str]
    actual: Optional[str]
    model_config = {"from_attributes": True}


class WeeklyRiskOut(BaseModel):
    id: int
    risk: str
    mitigation: str
    model_config = {"from_attributes": True}


class KeyGap(BaseModel):
    gap: str
    impact: Literal["high", "medium", "low"] = "medium"
    reason: str = ""


class WeeklyPlanCreate(BaseModel):
    week_start_date: date
    goal: str = ""
    context: str = ""


class WeeklyPlanUpdate(BaseModel):
    goal: Optional[str] = None
    context: Optional[str] = None
    prompt: Optional[str] = None
    status: Optional[PlanStatus] = None
    time_available_hours: Optional[int] = Field(None, ge=1, le=200)
    blockers: Optional[List[str]] = None
    focus_areas: Optional[List[str]] = None


class WeeklyPlanGenerate(BaseModel):
    prompt: str = ""
    goal: Optional[str] = None
    context: Optional[str] = None
    time_available_hours: Optional[int] = Field(None, ge=1, le=200)
    blockers: Optional[List[str]] = None
    focus_areas: Optional[List[str]] = None


class WeeklyPlanOut(BaseModel):
    id: int
    project_id: int
    week_start_date: date
    goal: str
    context: str
    prompt: str
    time_available_hours: int
    blockers: List[str]
    focus_areas: List[str]
    analysis_summary: str
    key_gaps: List[Dict[str, Any]]
    status: PlanStatus
    created_at: datetime
    updated_at: datetime
    plan_tasks: List[PlanTaskOut] = []
    metrics: List[WeeklyMetricOut] = []
    risks: List[WeeklyRiskOut] = []
    model_config = {"from_attributes": True}


# --- clarifier ---

ClarifyKind = Literal["project_intake", "weekly_intake"]


class ClarifyRequest(BaseModel):
    kind: ClarifyKind
    user_text: str = Field(..., min_length=1)
    known_fields: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[int] = None  # adds project context for weekly_intake


class ClarifyOption(BaseModel):
    label: str
    value: str


class ClarifyQuestion(BaseModel):
    field: str
    question: str
    multi_select: bool = True
    options: List[ClarifyOption]
    allow_custom: bool = True


class ClarifyResponse(BaseModel):
    summary: str
    questions: List[ClarifyQuestion]
