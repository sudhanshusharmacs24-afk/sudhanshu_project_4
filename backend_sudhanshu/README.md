# FastAPI Task Manager

This repository includes both a backend API and a frontend UI for managing tasks.

## What is included

- `main.py` — FastAPI backend for task CRUD operations
- `static/index.html` — frontend interface served by FastAPI
- `static/app.js` — frontend application logic
- `static/styles.css` — frontend styles
- `tasks.db` — SQLite database file created automatically

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

## Open in browser

- Frontend UI: `http://127.0.0.1:8000/`
- FastAPI docs: `http://127.0.0.1:8000/docs`

## Available API endpoints

| Method | URL | Description |
| --- | --- | --- |
| GET | `/` | Serve frontend UI |
| GET | `/tasks` | Get all tasks |
| POST | `/tasks` | Create new task |
| GET | `/tasks/{task_id}` | Get one task |
| PUT | `/tasks/{task_id}` | Update task |
| DELETE | `/tasks/{task_id}` | Delete task |

## Example JSON for creating a task

```json
{
  "title": "Complete homework",
  "description": "Finish FastAPI CRUD assignment"
}
```

## Example JSON for updating a task

```json
{
  "title": "Complete homework",
  "description": "Finish and submit assignment",
  "completed": true
}
```

Tasks are stored in `tasks.db`.
