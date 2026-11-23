from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DB_PATH = BASE_DIR / "jarvis.sqlite3"
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="J.A.R.V.I.S. API", version="0.1.0")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(db()) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class TaskUpdate(BaseModel):
    done: bool


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "online",
        "assistant": "J.A.R.V.I.S.",
        "ai_provider": "groq",
        "ai_configured": bool(os.getenv("GROQ_API_KEY")),
    }


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Groq is not configured. Add GROQ_API_KEY to your local .env file.",
        )

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are J.A.R.V.I.S., a capable, calm, concise personal AI assistant. "
                        "Be truthful about your capabilities. Never claim to have performed "
                        "an action unless a connected tool actually performed it. Do not "
                        "request or reveal secrets. Ask for confirmation before consequential actions."
                    ),
                },
                *[message.model_dump() for message in payload.messages],
            ],
            temperature=0.6,
        )
        answer = response.choices[0].message.content or ""
        return {"reply": answer}
    except HTTPException:
        raise
    except Exception as exc:
        # Do not expose provider response bodies, credentials, or internal details.
        raise HTTPException(
            status_code=502,
            detail="The AI provider request failed. Check your local configuration and try again.",
        ) from exc


@app.get("/api/tasks")
def list_tasks() -> list[dict]:
    with closing(db()) as connection:
        rows = connection.execute(
            "SELECT id, title, done, created_at FROM tasks ORDER BY created_at DESC"
        ).fetchall()
    return [
        {"id": row["id"], "title": row["title"], "done": bool(row["done"]), "created_at": row["created_at"]}
        for row in rows
    ]


@app.post("/api/tasks")
def create_task(payload: TaskCreate) -> dict:
    task_id = str(uuid.uuid4())
    with closing(db()) as connection:
        connection.execute(
            "INSERT INTO tasks (id, title) VALUES (?, ?)",
            (task_id, payload.title.strip()),
        )
        connection.commit()
    return {"id": task_id, "title": payload.title.strip(), "done": False}


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, payload: TaskUpdate) -> dict:
    with closing(db()) as connection:
        cursor = connection.execute(
            "UPDATE tasks SET done = ? WHERE id = ?",
            (int(payload.done), task_id),
        )
        connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "done": payload.done}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str) -> dict:
    with closing(db()) as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True, "id": task_id}
