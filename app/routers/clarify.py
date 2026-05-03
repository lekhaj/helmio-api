from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.services.clarifier import clarify

router = APIRouter(prefix="/clarify", tags=["clarify"])


@router.post("", response_model=schemas.ClarifyResponse)
def clarify_endpoint(body: schemas.ClarifyRequest, db: Session = Depends(get_db)):
    project_ctx = None
    if body.kind == "weekly_intake":
        if not body.project_id:
            raise HTTPException(status_code=422, detail="project_id required for weekly_intake")
        proj = db.get(models.Project, body.project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        project_ctx = {
            "name": proj.name,
            "vision": proj.vision,
            "stage": proj.stage.value if proj.stage else "mvp",
            "what_exists": proj.what_exists or [],
            "problems": proj.problems or [],
            "constraints": proj.constraints or [],
        }

    result = clarify(
        kind=body.kind,
        user_text=body.user_text,
        known=body.known_fields or {},
        project_ctx=project_ctx,
    )
    return result
