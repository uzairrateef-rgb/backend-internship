# BE-02: Connecting the CRUD API to SQLite

**Track:** Backend AI Engineering  
**Phase:** Foundations  
**Assignment:** BE-02 — Connecting to the Database  
**Technology:** Python, FastAPI, SQLite

## Overview

This project extends BE-01 by replacing in-memory task storage with a persistent SQLite database. It provides CRUD (Create, Read, Update, Delete) operations and demonstrates SQL-based searching, filtering, sorting, statistics, and timestamps.

SQLite was selected because it is lightweight, stores data in a single file, and does not require a separate database server.

## Architecture

```text
HTTP Client
    |
    v
FastAPI Application
    |
    v
SQLite Database
    |
    v
BE-02 Database/tasks.db
```

The API handles HTTP requests and responses. SQLite stores task records persistently, allowing data to survive application restarts.

## Project Structure

```text
BE-02 Database/
├── main.py
├── README.md
├── .gitignore
├── tasks.db                 # Generated locally; excluded from Git
└── docs/
    └── database-viewer.png
```

## Requirements

- Python 3.10 or later
- FastAPI
- Uvicorn
- Python's built-in `sqlite3` module

No separate SQLite server or database driver installation is required.

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/uzairrateef-rgb/backend-internship.git
cd backend-internship
```

### 2. Create and activate the virtual environment

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi "uvicorn[standard]"
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

### 3. Start the BE-02 application

Run from the repository root:

```bash
python -m uvicorn main:app --app-dir "BE-02 Database" --reload
```

On startup, the application automatically:

1. Creates the `tasks.db` file if missing.
2. Creates the `tasks` table if missing.
3. Adds timestamp columns to existing databases when necessary.
4. Inserts three example tasks when the table is empty.

### 4. Open the API documentation

- Swagger UI: http://127.0.0.1:8000/docs
- Root endpoint: http://127.0.0.1:8000/
- Health endpoint: http://127.0.0.1:8000/health

## Database Schema

The `tasks` table contains these columns:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Primary key identifying each task |
| `title` | TEXT | Task title |
| `done` | INTEGER | Completion status: `0` or `1` |
| `created_at` | TEXT | Timestamp when the task was created |
| `updated_at` | TEXT | Timestamp of the most recent update |

The application initializes missing timestamp columns in an existing database and fills missing timestamp values without deleting existing records.

## API Endpoints

| Method | Endpoint | Description | Success status |
|---|---|---|---|
| GET | `/` | API information | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List tasks | 200 |
| GET | `/tasks/{task_id}` | Retrieve one task | 200 |
| POST | `/tasks` | Create a task | 201 |
| PUT | `/tasks/{task_id}` | Update a task | 200 |
| DELETE | `/tasks/{task_id}` | Delete a task | 204 |
| GET | `/stats` | Task statistics | 200 |

Unknown task IDs return `404`. Invalid creation and update requests return `400`.

## Optional Features

### 1. Search using SQL

Search task titles using the `LIKE` operator.

```bash
curl -i "http://127.0.0.1:8000/tasks?search=milk"
```

The query searches for the supplied text within task titles. The search value is passed as a SQL parameter rather than inserted directly into the SQL statement.

### 2. Filter by completion status

Return only completed tasks:

```bash
curl -i "http://127.0.0.1:8000/tasks?done=true"
```

Return only pending tasks:

```bash
curl -i "http://127.0.0.1:8000/tasks?done=false"
```

The filter uses a SQL `WHERE` condition.

### 3. Sort tasks alphabetically

The default task listing is sorted alphabetically by title, ignoring case, with task ID as a secondary ordering key.

```bash
curl -i "http://127.0.0.1:8000/tasks"
```

The ordering is performed in SQL using `ORDER BY title COLLATE NOCASE, id`.

### 4. Task statistics

Retrieve aggregate statistics calculated directly in SQLite:

```bash
curl -i "http://127.0.0.1:8000/stats"
```

Example response:

```json
{
  "total": 5,
  "completed": 2,
  "pending": 3
}
```

The example counts are illustrative; actual values depend on the database.

The endpoint uses SQL `COUNT()` and `SUM()` expressions to calculate total, completed, and pending tasks.

### 5. Creation and update timestamps

Task responses include `created_at` and `updated_at`.

Example response:

```json
{
  "id": 1,
  "title": "Learn FastAPI",
  "done": false,
  "created_at": "2026-10-20 08:00:00",
  "updated_at": "2026-10-20 08:00:00"
}
```

The timestamp values above are illustrative.

- `created_at` records when a task was created.
- `updated_at` is refreshed when a task is updated.
- Existing database records are migrated without removing their task data.

### Example: Create a task

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Learn SQLite","done":false}'
```

### Example: Update a task

```bash
curl -i -X PUT http://127.0.0.1:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done":true}'
```

### Example: Delete a task

```bash
curl -i -X DELETE http://127.0.0.1:8000/tasks/1
```

## SQL Examples

The database can be inspected using the SQLite command-line tool or DB Browser for SQLite.

List every task:

```sql
SELECT * FROM tasks;
```

Show completed tasks:

```sql
SELECT * FROM tasks WHERE done = 1;
```

Count all tasks:

```sql
SELECT COUNT(*) FROM tasks;
```

Mark every task as completed:

```sql
UPDATE tasks SET done = 1;
```

Delete completed tasks:

```sql
DELETE FROM tasks WHERE done = 1;
```

Database changes are reflected in subsequent API requests because the application reads directly from SQLite.

## Database Screenshot

The following screenshot documents the `tasks` table and its stored records in DB Browser for SQLite.

![SQLite database viewer](docs/database-viewer.png)

## Persistence and Initialization

The database file is stored at:

`BE-02 Database/tasks.db`

The database file is generated locally and excluded from version control. Each fresh installation creates its own database automatically.

Example tasks are inserted when the table is empty. Existing records persist across application restarts.

## Implementation Notes

- Uses Python's built-in `sqlite3` library.
- Uses parameterized SQL for user-supplied values.
- Closes database connections after use.
- Converts SQLite completion values into JSON booleans.
- Initializes and migrates the database during application startup.
- Calculates task statistics using SQL aggregation.

## Learning Outcomes

This assignment demonstrates how to:

- Integrate SQLite with FastAPI.
- Initialize and migrate database schemas.
- Implement CRUD operations using SQL.
- Preserve data across server restarts.
- Validate requests and handle missing records.
- Search, filter, and sort data in SQL.
- Calculate statistics using aggregate queries.
- Track record creation and modification times.
- Inspect and modify records using a database viewer.

## Repository

[backend-internship on GitHub](https://github.com/uzairrateef-rgb/backend-internship)

**Assignment:** BE-02 — Connecting to the Database
