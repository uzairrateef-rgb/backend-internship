"""FastAPI application backed by SQLite."""

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "tasks.db"


def get_connection() -> sqlite3.Connection:
    """Return a database connection with named-column access."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create the tasks table and seed it only when empty."""
    connection = get_connection()

    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0
                        CHECK (done IN (0, 1))
                )
                """
            )

            task_count = connection.execute(
                "SELECT COUNT(*) FROM tasks"
            ).fetchone()[0]

            if task_count == 0:
                connection.executemany(
                    "INSERT INTO tasks (title, done) VALUES (?, ?)",
                    [
                        ("Learn FastAPI", 0),
                        ("Build a CRUD API", 0),
                        ("Connect SQLite database", 0),
                    ],
                )
    finally:
        connection.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize the database before serving requests."""
    initialize_database()
    yield


app = FastAPI(
    title="Backend Internship API",
    version="2.0.0",
    description="BE-02: SQLite database integration.",
    lifespan=lifespan,
)


def serialize_task(row: sqlite3.Row) -> dict:
    """Convert a database row into the public API representation."""
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
    }


@app.get("/")
def root() -> dict:
    """Return API information."""
    return {
        "name": "Backend Internship API",
        "version": "2.0.0",
        "database": "SQLite",
        "endpoints": {
            "health": "/health",
            "documentation": "/docs",
        },
    }


@app.get("/health")
def health() -> dict:
    """Report application health."""
    return {"status": "healthy"}


@app.get("/tasks")
def get_tasks() -> list[dict]:
    """Return all tasks stored in SQLite."""
    connection = get_connection()

    try:
        rows = connection.execute(
            "SELECT id, title, done FROM tasks ORDER BY id"
        ).fetchall()

        return [serialize_task(row) for row in rows]
    finally:
        connection.close()


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Return one task or a 404 response."""
    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if row is None:
            return JSONResponse(
                status_code=404,
                content={"error": "Task not found"},
            )

        return serialize_task(row)
    finally:
        connection.close()


@app.post(
    "/tasks",
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["title"],
                        "properties": {
                            "title": {"type": "string"},
                            "done": {"type": "boolean", "default": False},
                        },
                    }
                }
            },
        }
    },
)
async def create_task(request: Request):
    """Validate and persist a new task."""
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON body"},
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400,
            content={"error": "Request body must be a JSON object"},
        )

    title = payload.get("title")

    if not isinstance(title, str) or not title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required"},
        )

    done = payload.get("done", False)

    if not isinstance(done, bool):
        return JSONResponse(
            status_code=400,
            content={"error": "Done must be a boolean"},
        )

    connection = get_connection()

    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                (title.strip(), int(done)),
            )

            row = connection.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()

            return JSONResponse(
                status_code=201,
                content=serialize_task(row),
            )
    finally:
        connection.close()
