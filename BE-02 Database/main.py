
"""FastAPI application with automatic SQLite database initialization."""

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "tasks.db"


def get_connection() -> sqlite3.Connection:
    """Create and return a connection to the application database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create the tasks table and seed initial records when empty."""
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
                    """
                    INSERT INTO tasks (title, done)
                    VALUES (?, ?)
                    """,
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
    """Initialize persistent storage before the application starts."""
    initialize_database()
    yield


app = FastAPI(
    title="Backend Internship API",
    version="2.0.0",
    description="BE-02: SQLite database integration.",
    lifespan=lifespan,
)


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
