from __future__ import annotations
import os
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from examprep.env import ExamPrepEnv
from examprep.models import Action

app = FastAPI(title="ExamPrep OpenEnv", version="1.0.0")

_env: ExamPrepEnv = None


def get_env() -> ExamPrepEnv:
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first.")
    return _env


class ResetRequest(BaseModel):
    task: str = "easy"
    seed: int = 42


class StepRequest(BaseModel):
    action: Dict[str, Any]


@app.get("/", response_class=HTMLResponse)
def root():
    for path in [Path("dashboard.html"), Path("/app/dashboard.html")]:
        if path.exists():
            return path.read_text()
    return HTMLResponse("<h1>ExamPrep API running</h1>")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset(req: dict = {}):   # 👈 IMPORTANT CHANGE (NO Body)
    global _env

    task = req.get("task", "easy")
    seed = req.get("seed", 42)

    if task not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=400, detail="Choose easy | medium | hard")

    _env = ExamPrepEnv(task_name=task, seed=seed)
    obs = _env.reset()

    return {
        "observation": obs.model_dump(),
        "reward": None,
        "done": False,
        "info": {}
    }


@app.post("/step")
def step(req: StepRequest):
    env = get_env()
    try:
        action = Action(**req.action)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid action: {e}")
    try:
        result = env.step(action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(content=result.model_dump())


@app.get("/state")
def state():
    return JSONResponse(content=get_env().state())


@app.get("/tasks")
def list_tasks():
    return {"tasks": [
        {"name": "easy",   "description": "Single subject, 30 days, SSC CGL", "total_days": 30},
        {"name": "medium", "description": "3 subjects, 60 days, disruption at day 20", "total_days": 60},
        {"name": "hard",   "description": "Full UPSC, 90 days, bad mock + distraction", "total_days": 90},
    ]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("examprep.server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))