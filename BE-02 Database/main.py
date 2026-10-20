
"""FastAPI application backed by a persistent SQLite database."""

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


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


def error_response(status_code: int, message: str) -> JSONResponse:
    """Return a consistent API error response."""
    return JSONResponse(
        status_code=status_code,
        content={"error": message},
    )


async def read_json_body(request: Request):
    """Parse a JSON request body and return a clear validation error."""
    try:
        return await request.json(), None
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None, error_response(400, "Invalid JSON body")


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
            return error_response(404, "Task not found")

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
    payload, error = await read_json_body(request)
    if error:
        return error

    if not isinstance(payload, dict):
        return error_response(400, "Request body must be a JSON object")

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return error_response(400, "Title is required")

    done = payload.get("done", False)
    if not isinstance(done, bool):
        return error_response(400, "Done must be a boolean")

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


@app.put(
    "/tasks/{task_id}",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "done": {"type": "boolean"},
                        },
                    }
                }
            },
        }
    },
)
async def update_task(task_id: int, request: Request):
    """Update a task's title and/or completion status."""
    payload, error = await read_json_body(request)
    if error:
        return error

    if not isinstance(payload, dict):
        return error_response(400, "Request body must be a JSON object")

    if not payload or not set(payload).issubset({"title", "done"}):
        return error_response(400, "Provide a valid title or done field")

    updates = {}
    if "title" in payload:
        title = payload["title"]
        if not isinstance(title, str) or not title.strip():
            return error_response(400, "Title must be a non-empty string")
        updates["title"] = title.strip()

    if "done" in payload:
        done = payload["done"]
        if not isinstance(done, bool):
            return error_response(400, "Done must be a boolean")
        updates["done"] = int(done)

    connection = get_connection()

    try:
        with connection:
            existing = connection.execute(
                "SELECT id FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()

            if existing is None:
                return error_response(404, "Task not found")

            columns = ", ".join(f"{column} = ?" for column in updates)
            values = list(updates.values()) + [task_id]

            connection.execute(
                f"UPDATE tasks SET {columns} WHERE id = ?",
                values,
            )

            row = connection.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()

            return serialize_task(row)
    finally:
        connection.close()


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task or return 404 if it does not exist."""
    connection = get_connection()

    try:
        with connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,),
            )

            if cursor.rowcount == 0:
                return error_response(404, "Task not found")

        return Response(status_code=204)
    finally:
        connection.close()
