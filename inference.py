from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Any, Dict, List
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MODEL_NAME   = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN     = os.getenv("HF_TOKEN", "")
OPENAI_KEY   = os.getenv("OPENAI_API_KEY", "sk-placeholder")
MAX_STEPS    = 50

SYSTEM_PROMPT = """You are an expert AI study coach for Indian competitive exam students.

You receive the current state of a student's exam preparation journey and must decide the single best action to take right now.

Available action types:
- allocate_time: Assign study hours to a specific topic. Fields: topic_name, hours
- boost_topic: Increase priority for a weak topic. Fields: topic_name, new_priority (1-10)
- skip_topic: Deprioritise a topic already well covered. Fields: topic_name
- schedule_mock: Schedule a mock test. Fields: day_target
- replan: Restructure the study plan after a setback. Fields: reason
- diagnose_weakness: Analyse weak topics after a bad mock. Fields: subject
- report_progress: Log that the student studied a topic. Fields: topic_name, hours
- finalize_plan: Lock in the study plan. Fields: none

Respond ONLY with a valid JSON object:
{
  "action_type": "<type>",
  "topic_name": "<name or null>",
  "subject": "<subject or null>",
  "hours": null,
  "day_target": null,
  "new_priority": null,
  "reason": "<one sentence>"
}
No markdown, no extra text. Just JSON."""


def build_prompt(obs: Dict[str, Any]) -> str:
    weak = [t for t in obs["topics"] if t["mock_score"] and t["mock_score"] < 0.5]
    top  = sorted(obs["topics"], key=lambda t: t["priority"], reverse=True)[:5]
    return f"""DAY {obs['day']} of {obs['total_days']}
Coverage: {obs['overall_coverage']:.0%} | Projected: {obs['projected_score']:.0%} | Target: {obs['student']['target_score']:.0%}

ALERTS: {chr(10).join('- ' + a for a in obs.get('alerts', [])) or 'None'}

WEAK TOPICS:
{chr(10).join(f"- {t['name']} score={t['mock_score']:.0%}" for t in weak) or 'None'}

TOP PRIORITY TOPICS:
{chr(10).join(f"- {t['name']} ({t['subject']}) coverage={t['hours_spent']:.1f}/{t['estimated_hours']}h" for t in top)}

Available actions: {', '.join(obs['available_actions'])}

What is the best action right now?"""


def get_action(obs: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from openai import OpenAI
        if HF_TOKEN:
            client = OpenAI(api_key=HF_TOKEN, base_url="https://api-inference.huggingface.co/v1")
        else:
            client = OpenAI(api_key=OPENAI_KEY)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_prompt(obs)},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        top = sorted(obs["topics"], key=lambda t: t["priority"], reverse=True)[0]
        return {"action_type": "allocate_time", "topic_name": top["name"],
                "hours": min(3.0, obs["student"]["hours_per_day"]), "reason": f"fallback: {e}"}


def env_reset(task: str) -> Dict[str, Any]:
    r = requests.post(f"{API_BASE_URL}/reset", json={"task": task, "seed": 42})
    r.raise_for_status()
    return r.json()


def env_step(action: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{API_BASE_URL}/step", json={"action": action})
    r.raise_for_status()
    return r.json()


def run(task: str):
    print(f"[START] task={task} env=examprep model={MODEL_NAME}")
    obs = env_reset(task)
    rewards: List[float] = []
    step_n = 0
    success = False
    final_score = 0.0

    for step_n in range(1, MAX_STEPS + 1):
        action_dict = get_action(obs)
        try:
            result      = env_step(action_dict)
            reward      = result["reward"]["total"]
            done        = result["done"]
            info        = result["info"]
            obs         = result["observation"]
            rewards.append(reward)
            if done and "final_score" in info:
                final_score = info["final_score"]
                success = final_score >= obs["student"]["target_score"]
            action_str = f"{action_dict.get('action_type')}:{action_dict.get('topic_name') or ''}"
            print(f"[STEP] step={step_n} action={action_str} reward={reward:.2f} done={'true' if done else 'false'} error=null")
            if done:
                break
        except Exception as e:
            print(f"[STEP] step={step_n} action=error reward=0.00 done=false error={str(e)[:80]}")
            break

    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={'true' if success else 'false'} steps={step_n} score={final_score:.4f} rewards={rewards_str}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="easy", choices=["easy", "medium", "hard"])
    args = parser.parse_args()
    run(args.task)