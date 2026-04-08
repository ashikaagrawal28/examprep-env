from __future__ import annotations
import copy
import random
from typing import Any, Dict, List, Optional, Tuple
from examprep.models import (
    Action, ActionType, ExamType, MockTestResult,
    Observation, Reward, StudentProfile, StudyPlan,
    StepResult, Topic, TopicStatus
)
from examprep.curriculum import get_topics_for_exam
from examprep.grader import Grader


class ExamPrepEnv:
    def __init__(self, task_name: str = "easy", seed: int = 42):
        self.task_name = task_name
        self.seed = seed
        self._rng = random.Random(seed)
        self._grader = Grader()
        self._done = False
        self._step_count = 0
        self._mock_results: List[MockTestResult] = []
        self._day = 1
        self._total_days = 30
        self._prev_obs = None

    def reset(self):
        self._rng = random.Random(self.seed)
        self._done = False
        self._step_count = 0
        self._mock_results = []
        self._day = 1
        student, topics, plan = self._build_task(self.task_name)
        self._student = student
        self._topics = topics
        self._plan = plan
        obs = self._make_observation()
        self._prev_obs = copy.deepcopy(obs)
        return obs

    def step(self, action: Action) -> StepResult:
        if self._done:
            raise RuntimeError("Episode done. Call reset() first.")
        self._step_count += 1
        self._apply_action(action)
        self._simulate_day_progress()
        obs = self._make_observation()
        reward = self._grader.grade_action(action, self._prev_obs, obs)
        self._done = self._check_done(obs)
        info: Dict[str, Any] = {"step": self._step_count, "day": self._day, "task": self.task_name}
        if self._done:
            info["final_score"] = self._grader.final_score(obs)
        self._prev_obs = copy.deepcopy(obs)
        return StepResult(observation=obs, reward=reward, done=self._done, info=info)

    def state(self) -> Dict[str, Any]:
        return {
            "day": self._day,
            "task": self.task_name,
            "done": self._done,
            "step_count": self._step_count,
            "student": self._student.model_dump(),
            "topics": [t.model_dump() for t in self._topics],
            "plan": self._plan.model_dump() if self._plan else None,
            "mock_results": [m.model_dump() for m in self._mock_results],
        }

    def _build_task(self, task_name):
        builders = {"easy": self._build_easy_task, "medium": self._build_medium_task, "hard": self._build_hard_task}
        return builders[task_name]()

    def _build_easy_task(self):
        student = StudentProfile(
            student_id="s001", name="Ravi Kumar", exam=ExamType.SSC_CGL,
            months_remaining=1, hours_per_day=4.0, current_level=0.4,
            subjects=["Quantitative"], weak_subjects=["Geometry", "Trigonometry"], target_score=0.65,
        )
        all_topics = get_topics_for_exam("ssc_cgl")
        topics = [t for t in all_topics if t.subject == "Quantitative"]
        plan = StudyPlan(
            plan_id="plan_easy_001", student_id="s001", total_days=30,
            mock_test_days=[10, 20, 28],
            milestones={10: "Complete Number System + Algebra", 20: "Complete all topics", 28: "Final mock test"},
        )
        self._total_days = 30
        return student, topics, plan

    def _build_medium_task(self):
        student = StudentProfile(
            student_id="s002", name="Priya Sharma", exam=ExamType.SSC_CGL,
            months_remaining=2, hours_per_day=5.0, current_level=0.35,
            subjects=["Quantitative", "English", "Reasoning"],
            weak_subjects=["Vocabulary", "Syllogism"], target_score=0.70,
        )
        all_topics = get_topics_for_exam("ssc_cgl")
        topics = [t for t in all_topics if t.subject in ("Quantitative", "English", "Reasoning")]
        plan = StudyPlan(
            plan_id="plan_medium_001", student_id="s002", total_days=60,
            mock_test_days=[15, 30, 45, 58],
            milestones={15: "Quantitative basics done", 30: "English + Reasoning first pass", 45: "Full syllabus covered", 58: "Final revision complete"},
        )
        self._total_days = 60
        self._disruption_day = 20
        self._disruption_type = "illness"
        return student, topics, plan

    def _build_hard_task(self):
        student = StudentProfile(
            student_id="s003", name="Arjun Singh", exam=ExamType.UPSC,
            months_remaining=3, hours_per_day=6.0, current_level=0.30,
            subjects=["GS1", "GS2", "GS3", "GS4", "CSAT"],
            weak_subjects=["Indian Economy", "Ethics & Integrity", "World Geography"], target_score=0.75,
        )
        topics = get_topics_for_exam("upsc")
        plan = StudyPlan(
            plan_id="plan_hard_001", student_id="s003", total_days=90,
            mock_test_days=[20, 40, 60, 80, 88],
            milestones={20: "GS1 complete", 40: "GS2 + GS3 first pass", 60: "All GS subjects covered", 80: "Full revision", 88: "Final mock test"},
        )
        self._total_days = 90
        self._disruption_day = 30
        self._disruption_type = "bad_mock"
        self._second_disruption_day = 50
        self._second_disruption_type = "distraction"
        return student, topics, plan

    def _apply_action(self, action: Action):
        if action.action_type == ActionType.ALLOCATE_TIME:
            topic = self._find_topic(action.topic_name)
            if topic and action.hours:
                topic.hours_spent += action.hours
                topic.status = TopicStatus.COMPLETED if topic.coverage() >= 1.0 else TopicStatus.IN_PROGRESS
        elif action.action_type == ActionType.BOOST_TOPIC:
            topic = self._find_topic(action.topic_name)
            if topic:
                topic.priority = min(10, (action.new_priority or topic.priority) + 2)
                if action.hours:
                    topic.hours_spent += action.hours
        elif action.action_type == ActionType.SKIP_TOPIC:
            topic = self._find_topic(action.topic_name)
            if topic:
                topic.priority = max(1, topic.priority - 3)
        elif action.action_type == ActionType.SCHEDULE_MOCK:
            if action.day_target and self._plan:
                if action.day_target not in self._plan.mock_test_days:
                    self._plan.mock_test_days.append(action.day_target)
                    self._plan.mock_test_days.sort()
        elif action.action_type == ActionType.REPLAN:
            if self._plan:
                self._plan.last_revised_at_day = self._day
        elif action.action_type == ActionType.DIAGNOSE_WEAKNESS:
            if action.subject:
                for t in self._topics:
                    if t.subject == action.subject and t.mock_score and t.mock_score < 0.5:
                        t.status = TopicStatus.WEAK
        elif action.action_type == ActionType.REPORT_PROGRESS:
            topic = self._find_topic(action.topic_name)
            if topic and action.hours:
                topic.hours_spent += action.hours

    def _simulate_day_progress(self):
        self._day += 1
        if self._plan and self._day in self._plan.mock_test_days:
            self._run_mock_test()
        if hasattr(self, "_disruption_day") and self._day == self._disruption_day:
            self._apply_disruption(self._disruption_type)
        if hasattr(self, "_second_disruption_day") and self._day == self._second_disruption_day:
            self._apply_disruption(self._second_disruption_type)

    def _run_mock_test(self):
        subjects = list({t.subject for t in self._topics})
        subject_scores: Dict[str, float] = {}
        for subject in subjects:
            s_topics = [t for t in self._topics if t.subject == subject]
            avg_coverage = sum(t.coverage() for t in s_topics) / max(len(s_topics), 1)
            score = round(min(1.0, max(0.0, avg_coverage * 0.6 + self._student.current_level * 0.4 + self._rng.uniform(-0.05, 0.05))), 3)
            subject_scores[subject] = score
            for t in s_topics:
                t.mock_score = round(min(1.0, max(0.0, score + self._rng.uniform(-0.1, 0.1))), 3)
                if t.mock_score < 0.5:
                    t.status = TopicStatus.WEAK
        overall = round(sum(subject_scores.values()) / max(len(subject_scores), 1), 3)
        failed = [t.name for t in self._topics if t.mock_score and t.mock_score < 0.4]
        self._mock_results.append(MockTestResult(
            test_id=f"mock_{self._day}", day=self._day,
            subject_scores=subject_scores, overall_score=overall,
            time_taken_minutes=self._rng.randint(90, 120), topics_failed=failed,
        ))

    def _apply_disruption(self, disruption_type: str):
        if disruption_type == "illness":
            for t in self._topics:
                t.hours_spent = max(0, t.hours_spent - self._rng.uniform(0, 2))
        elif disruption_type == "bad_mock":
            if self._mock_results:
                last = self._mock_results[-1]
                last.overall_score = max(0.1, last.overall_score - 0.25)
                for k in last.subject_scores:
                    last.subject_scores[k] = max(0.1, last.subject_scores[k] - 0.2)
        elif disruption_type == "distraction":
            for t in self._topics:
                if t.status == TopicStatus.IN_PROGRESS:
                    t.hours_spent = max(0, t.hours_spent - 1.0)

    def _make_observation(self) -> Observation:
        overall_cov = self._weighted_coverage()
        projected   = self._project_score()
        days_behind = self._days_behind()
        alerts      = self._build_alerts(overall_cov, projected, days_behind)
        return Observation(
            day=self._day, total_days=self._total_days,
            student=self._student, topics=copy.deepcopy(self._topics),
            current_plan=copy.deepcopy(self._plan),
            recent_mock_results=self._mock_results[-3:],
            days_behind_schedule=days_behind,
            overall_coverage=round(overall_cov, 3),
            projected_score=round(projected, 3),
            alerts=alerts, available_actions=self._available_actions(),
        )

    def _weighted_coverage(self) -> float:
        total_w = sum(t.weight for t in self._topics)
        if total_w == 0:
            return 0.0
        return sum(t.coverage() * t.weight for t in self._topics) / total_w

    def _project_score(self) -> float:
        coverage = self._weighted_coverage()
        base = self._student.current_level
        if self._mock_results:
            mock_avg = sum(m.overall_score for m in self._mock_results) / len(self._mock_results)
            return round(coverage * 0.4 + base * 0.2 + mock_avg * 0.4, 3)
        return round(coverage * 0.6 + base * 0.4, 3)

    def _days_behind(self) -> int:
        if not self._plan or not self._plan.milestones:
            return 0
        missed = 0
        for milestone_day in self._plan.milestones:
            if self._day > milestone_day:
                cov = self._weighted_coverage()
                expected = milestone_day / self._total_days
                if cov < expected * 0.8:
                    missed += 1
        return missed * 3

    def _build_alerts(self, coverage, projected, behind) -> List[str]:
        alerts = []
        weak = [t for t in self._topics if t.is_weak()]
        if weak:
            alerts.append(f"{len(weak)} weak topics: {', '.join(t.name for t in weak[:3])}")
        if behind > 5:
            alerts.append(f"CRITICAL: {behind} days behind schedule. Replan now.")
        if projected < self._student.target_score * 0.7:
            alerts.append(f"Projected {projected:.0%} below target {self._student.target_score:.0%}")
        days_left = self._total_days - self._day
        if days_left < 10 and coverage < 0.7:
            alerts.append(f"Only {days_left} days left. {coverage:.0%} coverage. Prioritise now.")
        return alerts

    def _available_actions(self) -> List[ActionType]:
        actions = [ActionType.ALLOCATE_TIME, ActionType.BOOST_TOPIC, ActionType.SKIP_TOPIC,
                   ActionType.REPORT_PROGRESS, ActionType.RECOMMEND_RESOURCE]
        if self._plan:
            actions += [ActionType.SCHEDULE_MOCK, ActionType.REPLAN]
        if self._mock_results:
            actions.append(ActionType.DIAGNOSE_WEAKNESS)
        if self._day <= 3:
            actions.append(ActionType.FINALIZE_PLAN)
        return actions

    def _find_topic(self, name):
        if not name:
            return None
        return next((t for t in self._topics if t.name == name), None)

    def _check_done(self, obs) -> bool:
        if obs.day >= self._total_days:
            return True
        if obs.projected_score >= self._student.target_score:
            return True
        if (self._total_days - obs.day) < 5 and obs.projected_score < 0.2:
            return True
        return False