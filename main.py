
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Task Management API",
    description="A RESTful API for managing tasks, built with FastAPI.",
    version="1.0.0",
)

# In-memory task store
tasks = [
    {"id": 1, "title": "Complete backend assignment", "done": False},
    {"id": 2, "title": "Review Python fundamentals", "done": True},
    {"id": 3, "title": "Prepare project documentation", "done": False},
]


@app.get("/", tags=["General"], summary="API information")
def root():
    """Return basic information about the API."""
    return {
        "name": "Task Management API",
        "version": "1.0.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", tags=["General"], summary="Health check")
def health_check():
    """Confirm that the API is operational."""
    return {"status": "ok"}


@app.get("/tasks", tags=["Tasks"], summary="List all tasks")
def list_tasks():
    """Return all tasks."""
    return tasks


@app.get("/tasks/{task_id}", tags=["Tasks"], summary="Get a task by ID")
def get_task(task_id: int):
    """Return one task or a 404 error if it does not exist."""
    for task in tasks:
        if task["id"] == task_id:
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"},
    )
