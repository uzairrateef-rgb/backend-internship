
from fastapi import FastAPI

app = FastAPI(
    title="Task Management API",
    description="A RESTful API for managing tasks, built with FastAPI.",
    version="1.0.0",
)


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
