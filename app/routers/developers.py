from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/developers", tags=["developers"])


@router.get("/", response_model=List[schemas.DeveloperOut])
def list_developers(db: Session = Depends(get_db)):
    return db.query(models.Developer).order_by(models.Developer.name).all()


@router.post("/", response_model=schemas.DeveloperOut, status_code=status.HTTP_201_CREATED)
def create_developer(body: schemas.DeveloperCreate, db: Session = Depends(get_db)):
    dev = models.Developer(**body.model_dump())
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev


@router.delete("/{dev_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_developer(dev_id: int, db: Session = Depends(get_db)):
    dev = db.get(models.Developer, dev_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    db.delete(dev)
    db.commit()
