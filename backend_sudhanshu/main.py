from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DATABASE_NAME = "tasks.db"

app = FastAPI(
    title="Task Manager CRUD API",
    description="A simple FastAPI backend for creating, reading, updating, and deleting tasks.",
    version="1.0.0",
)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    completed: Optional[bool] = None


class Task(TaskCreate):
    id: int
    completed: bool
    created_at: str


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )


def row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"]),
        created_at=row["created_at"],
    )


@app.on_event("startup")
def startup() -> None:
    create_table()


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate) -> Task:
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (title, description, created_at)
            VALUES (?, ?, ?)
            """,
            (task.title, task.description, created_at),
        )
        task_id = cursor.lastrowid
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    return row_to_task(row)


@app.get("/tasks", response_model=list[Task])
def get_tasks() -> list[Task]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM tasks ORDER BY id").fetchall()

    return [row_to_task(row) for row in rows]


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int) -> Task:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return row_to_task(row)


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskUpdate) -> Task:
    existing_task = get_task(task_id)

    updated_title = task.title if task.title is not None else existing_task.title
    updated_description = (
        task.description if task.description is not None else existing_task.description
    )
    updated_completed = (
        task.completed if task.completed is not None else existing_task.completed
    )

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, completed = ?
            WHERE id = ?
            """,
            (updated_title, updated_description, int(updated_completed), task_id),
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    return row_to_task(row)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    get_task(task_id)

    with get_connection() as connection:
        connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    return {"message": "Task deleted successfully"}
