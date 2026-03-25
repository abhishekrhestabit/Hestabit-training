from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from . import services, schemas, database
from typing import List

router = APIRouter()

@router.post("/tasks/", response_model=schemas.Task)
def create(task: schemas.TaskCreate, db: Session = Depends(database.get_db)):
    return services.create_task(db, task)

@router.get("/tasks/{task_id}", response_model=schemas.Task)
def read(task_id: int, db: Session = Depends(database.get_db)):
    return services.get_task(db, task_id)

@router.put("/tasks/{task_id}", response_model=schemas.Task)
def update(task_id: int, task: schemas.TaskCreate, db: Session = Depends(database.get_db)):
    return services.update_task(db, task_id, task)

@router.delete("/tasks/{task_id}")
def delete(task_id: int, db: Session = Depends(database.get_db)):
    return services.delete_task(db, task_id)
