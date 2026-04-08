from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExamType(str, Enum):
    UPSC    = "upsc"
    SSC_CGL = "ssc_cgl"
    NEET    = "neet"
    JEE     = "jee"
    PSC     = "psc"


class ActionType(str, Enum):
    ALLOCATE_TIME      = "allocate_time"
    SCHEDULE_MOCK      = "schedule_mock"
    REPORT_PROGRESS    = "report_progress"
    DIAGNOSE_WEAKNESS  = "diagnose_weakness"
    REPLAN             = "replan"
    RECOMMEND_RESOURCE = "recommend_resource"
    SKIP_TOPIC         = "skip_topic"
    BOOST_TOPIC        = "boost_topic"
    FINALIZE_PLAN      = "finalize_plan"


class TopicStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    WEAK        = "weak"
    STRONG      = "strong"


class Topic(BaseModel):
    name: str
    subject: str
    weight: float
    estimated_hours: float
    status: TopicStatus = TopicStatus.NOT_STARTED
    hours_spent: float = 0.0
    mock_score: Optional[float] = None
    priority: int = 5

    def coverage(self) -> float:
        if self.estimated_hours == 0:
            return 1.0
        return min(self.hours_spent / self.estimated_hours, 1.0)

    def is_weak(self) -> bool:
        return self.mock_score is not None and self.mock_score < 0.5


class StudentProfile(BaseModel):
    student_id: str
    name: str
    exam: ExamType
    months_remaining: int
    hours_per_day: float
    current_level: float
    subjects: List[str]
    weak_subjects: List[str] = Field(default_factory=list)
    target_score: float


class MockTestResult(BaseModel):
    test_id: str
    day: int
    subject_scores: Dict[str, float]
    overall_score: float
    time_taken_minutes: int
    topics_failed: List[str] = Field(default_factory=list)


class StudyPlan(BaseModel):
    plan_id: str
    student_id: str
    total_days: int
    daily_schedule: Dict[int, Dict[str, float]] = Field(default_factory=dict)
    mock_test_days: List[int] = Field(default_factory=list)
    milestones: Dict[int, str] = Field(default_factory=dict)
    created_at_day: int = 0
    last_revised_at_day: Optional[int] = None


class Observation(BaseModel):
    day: int
    total_days: int
    student: StudentProfile
    topics: List[Topic]
    current_plan: Optional[StudyPlan]
    recent_mock_results: List[MockTestResult] = Field(default_factory=list)
    days_behind_schedule: int = 0
    overall_coverage: float = 0.0
    projected_score: float = 0.0
    alerts: List[str] = Field(default_factory=list)
    available_actions: List[ActionType]


class Action(BaseModel):
    action_type: ActionType
    topic_name: Optional[str] = None
    subject: Optional[str] = None
    hours: Optional[float] = None
    day_target: Optional[int] = None
    new_priority: Optional[int] = None
    resource_type: Optional[str] = None
    reason: Optional[str] = None
    schedule_updates: Optional[Dict[str, Any]] = None


class Reward(BaseModel):
    total: float
    coverage_delta: float = 0.0
    weak_topic_improvement: float = 0.0
    mock_score_improvement: float = 0.0
    plan_efficiency: float = 0.0
    proactive_bonus: float = 0.0
    deadline_penalty: float = 0.0
    redundancy_penalty: float = 0.0
    recovery_bonus: float = 0.0
    breakdown: Dict[str, float] = Field(default_factory=dict)
    message: str = ""


class StepResult(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)