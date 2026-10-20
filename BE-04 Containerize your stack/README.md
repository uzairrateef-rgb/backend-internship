# BE-04: Containerize Your Stack

## Overview

A task management REST API built with FastAPI and PostgreSQL, containerized with Docker and Docker Compose.

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL 18
- Psycopg
- Docker
- Docker Compose

## Project Structure

```text
BE-04 Containerize your stack/
├── Dockerfile
├── compose.yaml
├── main.py
├── repository.py
├── requirements.txt
├── .env.example
├── .gitignore
├── sql/
│   └── init.sql
└── README.md
```

## Prerequisites

- Docker Desktop installed and running
- Docker Compose available

## Configuration

The application reads its database connection from `DATABASE_URL`.

Copy `.env.example` to `.env` for local development and configure the connection string as required. The Compose configuration supplies the database connection to the API container.

## Run the Application

From this directory, run:

```bash
docker compose up --build
```

To run in the background:

```bash
docker compose up --build -d
```

To stop the application:

```bash
docker compose down
```

The PostgreSQL database uses the named Docker volume `taskdata` to persist data across container restarts.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | API and database health |
| GET | `/tasks` | List all tasks |
| GET | `/tasks/{task_id}` | Retrieve one task |
| POST | `/tasks` | Create a task |
| PUT | `/tasks/{task_id}` | Update a task |
| DELETE | `/tasks/{task_id}` | Delete a task |

## Example Requests

Check the health endpoint:

```bash
curl -i http://localhost:8000/health
```

Example response:

```json
HTTP/1.1 200 OK
date: Tue, 20 Oct 2026 14:43:23 GMT
server: uvicorn
content-length: 31
content-type: application/json

{"status":"ok","database":"ok"}
```

List tasks:

```bash
curl http://localhost:8000/tasks
```

Create a task:

```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Example task","done":false}'
```

## Persistence Verification

The application and database were stopped and restarted using Docker Compose. The health endpoint returned `200 OK`, and previously stored tasks remained available after the restart.

### Database Evidence

The screenshot in `docs/database-evidence.png` shows the PostgreSQL
tasks table and its persisted records.

## Security Notes

- `.env` contains local configuration and must not be committed.
- `.env.example` documents the required configuration.
- The example database credentials are for local development only and should be replaced for production use.
