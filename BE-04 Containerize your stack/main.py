"""FastAPI task API backed by PostgreSQL."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

import repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize PostgreSQL before serving requests."""
    repository.initialize_database()
    yield


app = FastAPI(
    title="Task Management API",
    description="A task CRUD API backed by PostgreSQL.",
    version="3.0.0",
    lifespan=lifespan,
)


def find_task(task_id: int):
    """Return a task by ID."""
    return repository.get_task(task_id)


@app.get("/", tags=["General"])
def root():
    return {
        "name": "Task Management API",
        "version": "3.0.0",
        "database": "PostgreSQL",
        "endpoints": [
            "/health",
            "/tasks",
            "/tasks/{task_id}",
        ],
    }


@app.get("/health", tags=["General"])
def health_check():
    try:
        repository.list_tasks()
        return {"status": "ok", "database": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )


@app.get("/tasks", tags=["Tasks"])
def list_tasks():
    return repository.list_tasks()


@app.get("/tasks/{task_id}", tags=["Tasks"])
def get_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )
    return task


@app.post("/tasks", status_code=201, tags=["Tasks"])
async def create_task(request: Request):
    try:
        data = await request.json()
    except (ValueError, UnicodeDecodeError):
        return JSONResponse(
            status_code=400,
            content={"error": "Request body must contain valid JSON"},
        )

    if not isinstance(data, dict):
        return JSONResponse(
            status_code=400,
            content={"error": "Request body must be a JSON object"},
        )

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return JSONResponse(
            status_code=400,
            content={
                "error": "Title is required and must be a non-empty string"
            },
        )

    done = data.get("done", False)
    if not isinstance(done, bool):
        return JSONResponse(
            status_code=400,
            content={"error": "Done must be a boolean"},
        )

    task = repository.create_task(title.strip(), done)
    return JSONResponse(status_code=201, content=task)


@app.put("/tasks/{task_id}", tags=["Tasks"])
async def update_task(task_id: int, request: Request):
    if find_task(task_id) is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )

    try:
        data = await request.json()
    except (ValueError, UnicodeDecodeError):
        return JSONResponse(
            status_code=400,
            content={"error": "Request body must contain valid JSON"},
        )

    if not isinstance(data, dict) or not data:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Request body must be a non-empty JSON object"
            },
        )

    if set(data) - {"title", "done"}:
        return JSONResponse(
            status_code=400,
            content={"error": "Only title and done fields are allowed"},
        )

    title = data.get("title")
    if "title" in data:
        if not isinstance(title, str) or not title.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Title must be a non-empty string"},
            )
        title = title.strip()

    done = data.get("done")
    if "done" in data and not isinstance(done, bool):
        return JSONResponse(
            status_code=400,
            content={"error": "Done must be a boolean"},
        )

    task = repository.update_task(
        task_id,
        title=title,
        done=done,
    )

    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )

    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    tags=["Tasks"],
)
def delete_task(task_id: int):
    if not repository.delete_task(task_id):
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )
    return Response(status_code=204)
