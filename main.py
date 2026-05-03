from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from app.database import engine, Base
from app.routers import tasks, feedback, projects, developers, weekly_plans, plan_tasks

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Helmio API", version="0.2.0")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(feedback.router)
app.include_router(projects.router)
app.include_router(developers.router)
app.include_router(weekly_plans.router)
app.include_router(plan_tasks.router)


@app.get("/health")
def health():
    return {"status": "ok"}
