<div align="center">
 
```
███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██████╗ ███████╗██████╗
██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██╔══██╗██╔════╝██╔══██╗
█████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██████╔╝█████╗  ██████╔╝
██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██╔══██╗██╔══╝  ██╔═══╝
███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ██║  ██║███████╗██║
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝
```
 
**OpenEnv · Competitive Exam Preparation Agent · **
 
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-orange.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![OpenEnv Spec](https://img.shields.io/badge/OpenEnv-v1.0-blueviolet.svg)](openenv.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
 
</div>
 
---
 
## The Problem
 
> *Every year, **2.5 crore Indians** sit for UPSC, SSC, NEET, JEE, and state PSCs. Most are from small cities. Most cannot afford coaching. Most study the wrong things — and fail not because they aren't smart, but because nobody told them what to focus on.*
 
ExamPrep OpenEnv puts an AI agent in the role of personal study planner. It receives a student's exam, level, and time left — and must build a day-by-day plan, track real progress, diagnose failures, and recover before exam day.
 
**Supported exams:** `upsc` · `ssc_cgl` · `neet` · `jee` · `psc`
 
---
 
## Observation Space
 
```python
class Observation(BaseModel):
    day: int                              # Current day (1-indexed)
    total_days: int                       # Days until exam
    student: StudentProfile               # Exam, level, hours/day, target score
    topics: List[Topic]                   # All topics with coverage + mock scores
    current_plan: Optional[StudyPlan]     # Active day-by-day schedule
    recent_mock_results: List[MockTestResult]
    days_behind_schedule: int             # Schedule drift
    overall_coverage: float               # Weighted syllabus coverage [0–1]
    projected_score: float                # Estimated exam-day score
    alerts: List[str]                     # Warnings: weak topics, deadlines
    available_actions: List[ActionType]   # Legal actions this step
```
 
Each `Topic` carries: `name · subject · weight [0–1] · estimated_hours · hours_spent · status · mock_score · priority [1–10]`
 
---
 
## Action Space
 
| Action | What it does |
|---|---|
| `allocate_time` | Assign study hours to a topic today |
| `schedule_mock` | Book a mock test on a target day |
| `report_progress` | Log hours studied for a topic |
| `diagnose_weakness` | Flag a topic as weak with a reason |
| `replan` | Rebuild the full schedule from today |
| `recommend_resource` | Suggest a resource for a topic |
| `skip_topic` | Deprioritize a low-weight topic |
| `boost_topic` | Raise priority on weak/high-weight topic |
| `finalize_plan` | Commit the current plan as active |
 
---
 
## Reward Function
 
Dense, deterministic, 8 components — computed every step:
 
```
reward = coverage_delta         (+) weighted syllabus progress
       + weak_topic_improvement (+) score gain on flagged weak topics
       + mock_score_improvement (+) improvement in mock test performance
       + plan_efficiency        (+) time on high-weight vs low-weight topics
       + proactive_bonus        (+) acting on alerts before they become crises
       + recovery_bonus         (+) closing schedule gaps after falling behind
       − deadline_penalty       (−) high-weight topics uncovered near exam day
       − redundancy_penalty     (−) over-studying already-strong topics
```
 
Terminal bonus/penalty applied on the final day based on `projected_score` vs `target_score`.
 
---
 
## Tasks
 
### 🟢 Easy — 30-Day Single Subject Plan
> One subject. No disruptions. Build and execute.
 
**Setup:** 30 days · UPSC GS1 History · 4 hrs/day  
**Goal:** `coverage ≥ 0.80`, all topics with `weight > 0.07` completed, ≥ 2 mock tests  
**Baseline:** `0.72` *(greedy highest-weight-first, no replanning)*
 
---
 
### 🟡 Medium — 3 Subjects + Mock Schedule + Disruption
> Balance three subjects. Physics falls behind on day 35. Recover.
 
**Setup:** 90 days · NEET (Biology + Physics + Chemistry) · 6 hrs/day · 3-day disruption at day 35  
**Goal:** All subjects `coverage ≥ 0.75`, none below `0.60`, projected score ≥ 80% of target  
**Baseline:** `0.54` *(equal-time split, ignores disruptions)*
 
---
 
### 🔴 Hard — Mock Test Failure Diagnosis + Full Recovery
> Student scores 38% on Day 42. 78 days left. Diagnose. Recover.
 
**Setup:** 120 days · UPSC · GS1 29% · GS2 44% · GS3 41% · GS4 62% · target 65%  
**Goal:** Diagnose weak topics → restructure plan → verify via mocks every 14 days → `projected_score ≥ 0.65` by day 120  
**Baseline:** `0.31` *(uniform hour increase, no diagnosis)*
 
---
 
## Baseline Summary
 
| Task | Difficulty | Baseline | Beat this |
|---|---|---|---|
| 30-day single subject | 🟢 Easy | 0.72 | ≥ 0.85 |
| 3-subject + disruption | 🟡 Medium | 0.54 | ≥ 0.75 |
| Mock failure recovery | 🔴 Hard | 0.31 | ≥ 0.70 |
 
*Scores are on a 0.0–1.0 scale.*
 
---
 
## Setup
 
```bash
# 1. Create and enter project folder
mkdir examprep-env && cd examprep-env
 
# 2. Virtual environment
python -m venv venv
venv\Scripts\activate           # Windows
source venv/bin/activate        # Mac/Linux
 
# 3. Install dependencies
pip install fastapi uvicorn pydantic openai requests python-multipart
```
 
**File structure:**
```
examprep-env/
├── examprep/
│   ├── __init__.py     ← package exports
│   ├── models.py       ← Observation, Action, Reward
│   ├── curriculum.py   ← UPSC / SSC / NEET syllabi
│   ├── grader.py       ← reward computation
│   ├── env.py          ← simulation engine
│   └── server.py       ← FastAPI endpoints
├── inference.py        ← LLM agent
├── openenv.yaml
├── Dockerfile
└── requirements.txt
```
 
---
 
## Usage
 
```bash
# Start the environment server
uvicorn examprep.server:app --host 0.0.0.0 --port 8000
 
# Run the agent
python inference.py --task easy
python inference.py --task medium
python inference.py --task hard
```
 
**API:**
 
| Method | Endpoint | Description |
|---|---|---|
| POST | `/reset` | Initialize with student profile |
| POST | `/step` | Submit action → observation + reward |
| GET | `/state` | Inspect current state |
 
**Docker:**
```bash
docker build -t examprep-env .
docker run -p 8000:8000 examprep-env
```
 
**Agent stdout format:**
```
[START]
[STEP] diagnose_weakness | topic: Ancient Indian History | reason: mock_score=0.28
[STEP] boost_topic       | topic: Ancient Indian History | priority: 9
[STEP] replan            | GS1: 3.0h/day · GS2: 1.5h/day · GS3: 1.5h/day
[END]
```
 
---
 
<div align="center">
 
*Built for the OpenEnv Hackathon · MIT License*  

</div>