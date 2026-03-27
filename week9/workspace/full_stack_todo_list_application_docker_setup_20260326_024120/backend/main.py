from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import models, database
from pydantic import BaseModel

app = FastAPI()

# Create tables
models.Base.metadata.create_all(bind=database.engine)

class TodoCreate(BaseModel):
    title: str
    description: str = None

class TodoResponse(TodoCreate):
    id: int
    completed: bool

    class Config:
        from_attributes = True

@app.get("/todos", response_model=List[TodoResponse])
def read_todos(db: Session = Depends(database.get_db)):
    return db.query(models.Todo).all()

@app.post("/todos", response_model=TodoResponse)
def create_todo(todo: TodoCreate, db: Session = Depends(database.get_db)):
    db_todo = models.Todo(**todo.dict())
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

@app.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, db: Session = Depends(database.get_db)):
    db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    db_todo.completed = not db_todo.completed
    db.commit()
    return db_todo
