"""PostgreSQL repository for task storage."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Configure it in the .env file."
    )

SEED_TASKS = [
    ("Complete backend assignment", False),
    ("Review Python fundamentals", True),
    ("Prepare project documentation", False),
]


def get_connection():
    """Open a PostgreSQL connection that returns dictionary-like rows."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def initialize_database() -> None:
    """Create the table and seed tasks only if the table is empty."""
    schema_path = BASE_DIR / "sql" / "init.sql"
    schema = schema_path.read_text(encoding="utf-8")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema)
            cursor.execute("SELECT COUNT(*) AS count FROM tasks")
            result = cursor.fetchone()

            if result["count"] == 0:
                cursor.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    SEED_TASKS,
                )


def list_tasks() -> list[dict]:
    """Return all tasks ordered by ID."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, done FROM tasks ORDER BY id"
            )
            return cursor.fetchall()


def get_task(task_id: int) -> dict | None:
    """Return one task, or None when it does not exist."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s",
                (task_id,),
            )
            return cursor.fetchone()


def create_task(title: str, done: bool = False) -> dict:
    """Insert a task and return its generated ID."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (title, done)
                VALUES (%s, %s)
                RETURNING id, title, done
                """,
                (title, done),
            )
            return cursor.fetchone()


def update_task(
    task_id: int,
    title: str | None = None,
    done: bool | None = None,
) -> dict | None:
    """Update supplied fields and return the task, or None if missing."""
    if title is None and done is None:
        return get_task(task_id)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET title = COALESCE(%s, title),
                    done = COALESCE(%s, done)
                WHERE id = %s
                RETURNING id, title, done
                """,
                (title, done, task_id),
            )
            return cursor.fetchone()


def delete_task(task_id: int) -> bool:
    """Delete a task and return whether a row was deleted."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tasks WHERE id = %s RETURNING id",
                (task_id,),
            )
            return cursor.fetchone() is not None
