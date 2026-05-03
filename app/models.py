from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Date, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


# --- existing simple task tracker (kept) ---

class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(TaskStatus), default=TaskStatus.todo, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    feedback = relationship("Feedback", back_populates="task", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="feedback")


# --- sprint planner ---

class ProjectStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class ProjectStage(str, enum.Enum):
    idea = "idea"
    mvp = "mvp"
    early_users = "early_users"
    growth = "growth"
    scaling = "scaling"


class PlanStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class PlanTaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class Developer(Base):
    __tablename__ = "developers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    role = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plan_tasks = relationship("PlanTask", back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    description = Column(Text, default="")
    # rich context (filled via clarifier)
    vision = Column(Text, default="")
    target_user = Column(Text, default="")
    stage = Column(Enum(ProjectStage), default=ProjectStage.mvp, nullable=False)
    constraints = Column(JSONB, default=list)         # list[str]
    what_exists = Column(JSONB, default=list)         # list[str]
    problems = Column(JSONB, default=list)            # list[str]
    # legacy KPI fields kept for compat
    kpi_primary = Column(String(255), nullable=True)
    kpi_secondary = Column(String(255), nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.active, nullable=False)
    color = Column(String(16), default="violet")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    weekly_plans = relationship("WeeklyPlan", back_populates="project", cascade="all, delete-orphan")


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    goal = Column(Text, default="")
    context = Column(Text, default="")
    prompt = Column(Text, default="")
    # rich plan inputs
    time_available_hours = Column(Integer, default=35, nullable=False)
    blockers = Column(JSONB, default=list)            # list[str]
    focus_areas = Column(JSONB, default=list)         # list[str]
    # rich plan outputs
    analysis_summary = Column(Text, default="")
    key_gaps = Column(JSONB, default=list)            # list[{gap, impact, reason}]
    llm_response_raw = Column(JSONB, nullable=True)
    status = Column(Enum(PlanStatus), default=PlanStatus.draft, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="weekly_plans")
    plan_tasks = relationship(
        "PlanTask", back_populates="weekly_plan", cascade="all, delete-orphan",
        order_by="PlanTask.order_index",
    )
    metrics = relationship("WeeklyMetric", back_populates="weekly_plan", cascade="all, delete-orphan")
    risks = relationship("WeeklyRisk", back_populates="weekly_plan", cascade="all, delete-orphan")


class PlanTask(Base):
    __tablename__ = "plan_tasks"
    id = Column(Integer, primary_key=True, index=True)
    weekly_plan_id = Column(Integer, ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    assignee_id = Column(Integer, ForeignKey("developers.id", ondelete="SET NULL"), nullable=True)
    effort_hours = Column(Integer, default=4, nullable=False)
    priority = Column(Enum(Priority), default=Priority.medium, nullable=False)
    status = Column(Enum(PlanTaskStatus), default=PlanTaskStatus.todo, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    # NEW
    day_index = Column(Integer, nullable=True)        # 0..4 = Mon..Fri, null = unscheduled
    expected_outcome = Column(Text, default="")
    depends_on = Column(JSONB, default=list)          # list[str] (task titles)
    is_handoff = Column(Boolean, default=False)       # true when work goes to artist/QA
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    weekly_plan = relationship("WeeklyPlan", back_populates="plan_tasks")
    assignee = relationship("Developer", back_populates="plan_tasks")


class WeeklyMetric(Base):
    __tablename__ = "weekly_metrics"
    id = Column(Integer, primary_key=True, index=True)
    weekly_plan_id = Column(Integer, ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    target = Column(String(255), default="")
    linked_task_titles = Column(JSONB, default=list)  # list[str]
    actual = Column(String(255), nullable=True)       # filled at week-end
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    weekly_plan = relationship("WeeklyPlan", back_populates="metrics")


class WeeklyRisk(Base):
    __tablename__ = "weekly_risks"
    id = Column(Integer, primary_key=True, index=True)
    weekly_plan_id = Column(Integer, ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=False)
    risk = Column(Text, nullable=False)
    mitigation = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    weekly_plan = relationship("WeeklyPlan", back_populates="risks")
