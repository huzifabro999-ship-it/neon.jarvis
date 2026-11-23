# J.A.R.V.I.S. — Personal AI Assistant

A modular personal assistant with a neon dashboard, FastAPI backend, and Groq-powered chat.

## Requirements
- Python 3.10+
- A Groq API key
- Windows, macOS, or Linux

## Setup
1. Create and activate a virtual environment:
   `python -m venv .venv`
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`.
4. Add your own Groq API key to `.env`. Never commit this file.
5. Start the server:
   `uvicorn app.main:app --reload`
6. Open http://127.0.0.1:8000

## Configuration
- `GROQ_API_KEY`: your private Groq key
- `GROQ_MODEL`: model ID available to your Groq account
- `APP_HOST` / `APP_PORT`: local server binding

The dashboard is served by FastAPI. Chat requests are sent to the backend; the API key remains server-side.

## API
- `GET /api/health` — service and provider configuration status
- `POST /api/chat` — send a message and receive an assistant response
- `GET /api/tasks` — list locally stored tasks
- `POST /api/tasks` — create a task
- `PATCH /api/tasks/{task_id}` — update task completion
- `DELETE /api/tasks/{task_id}` — delete a task

Interactive API documentation: http://127.0.0.1:8000/docs

## Safety and privacy
JARVIS does not execute arbitrary shell commands. The first release is a local chat and task dashboard. Desktop automation, microphone access, reminders, and external integrations must be added as separately permissioned modules. Do not expose this development server to the public internet without authentication and transport security.

## Project status
Phase 1 foundation: local dashboard, health endpoint, Groq chat, and SQLite task storage.
