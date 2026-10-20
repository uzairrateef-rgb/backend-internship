
from fastapi import FastAPI, Request, Response
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


def find_task(task_id: int):
    """Find a task by ID, or return None."""
    return next((task for task in tasks if task["id"] == task_id), None)


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
    task = find_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )
    return task



@app.post(
    "/tasks",
    status_code=201,
    tags=["Tasks"],
    summary="Create a task",
    description="Create a task with a required, non-empty title.",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["title"],
                        "properties": {
                            "title": {
                                "type": "string",
                                "minLength": 1,
                                "example": "Buy milk",
                            }
                        },
                    }
                }
            },
        }
    },
)

async def create_task(request: Request):
    """Create a task after validating the request body."""
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
            content={"error": "Title is required and must be a non-empty string"},
        )

    task = {
        "id": max((task["id"] for task in tasks), default=0) + 1,
        "title": title.strip(),
        "done": False,
    }
    tasks.append(task)
    return JSONResponse(status_code=201, content=task)



@app.put(
    "/tasks/{task_id}",
    tags=["Tasks"],
    summary="Update a task",
    description="Update a task's title, completion status, or both.",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "minProperties": 1,
                        "properties": {
                            "title": {
                                "type": "string",
                                "example": "Finish API documentation",
                            },
                            "done": {
                                "type": "boolean",
                                "example": True,
                            },
                        },
                    }
                }
            },
        }
    },
)

async def update_task(task_id: int, request: Request):
    """Update a task's title and/or completion status."""
    task = find_task(task_id)
    if task is None:
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
            content={"error": "Request body must be a non-empty JSON object"},
        )

    if set(data) - {"title", "done"}:
        return JSONResponse(
            status_code=400,
            content={"error": "Only title and done fields are allowed"},
        )

    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Title must be a non-empty string"},
            )

    if "done" in data and not isinstance(data["done"], bool):
        return JSONResponse(
            status_code=400,
            content={"error": "Done must be a boolean"},
        )

    if "title" in data:
        task["title"] = data["title"].strip()

    if "done" in data:
        task["done"] = data["done"]

    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    tags=["Tasks"],
    summary="Delete a task",
)
def delete_task(task_id: int):
    """Delete a task or return 404 if it does not exist."""
    task = find_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )

    tasks.remove(task)
    return Response(status_code=204)
