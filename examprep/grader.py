from __future__ import annotations
from typing import List, TYPE_CHECKING
from examprep.models import Action, ActionType, Observation, Reward, Topic


class Grader:
    COVERAGE_WEIGHT         = 0.30
    WEAK_IMPROVEMENT_WEIGHT = 0.25
    MOCK_IMPROVEMENT_WEIGHT = 0.20
    EFFICIENCY_WEIGHT       = 0.15
    PROACTIVE_WEIGHT        = 0.10

    DEADLINE_PENALTY        = -0.25
    REDUNDANCY_PENALTY      = -0.10
    RECOVERY_BONUS          = +0.20

    def grade_action(self, action, obs_before, obs_after):
        coverage_delta   = self._coverage_delta(obs_before, obs_after)
        weak_improvement = self._weak_topic_improvement(action, obs_before, obs_after)
        mock_improvement = self._mock_score_improvement(obs_before, obs_after)
        efficiency       = self._plan_efficiency(action, obs_before)
        proactive        = self._proactive_bonus(action, obs_before)
        deadline_pen     = self._deadline_penalty(obs_after)
        redundancy_pen   = self._redundancy_penalty(action, obs_before)
        recovery         = self._recovery_bonus(obs_before, obs_after)

        total = (
            coverage_delta        * self.COVERAGE_WEIGHT
            + weak_improvement    * self.WEAK_IMPROVEMENT_WEIGHT
            + mock_improvement    * self.MOCK_IMPROVEMENT_WEIGHT
            + efficiency          * self.EFFICIENCY_WEIGHT
            + proactive           * self.PROACTIVE_WEIGHT
            + deadline_pen
            + redundancy_pen
            + recovery
        )
        total = max(-1.0, min(1.0, total))

        return Reward(
            total=round(total, 4),
            coverage_delta=round(coverage_delta, 4),
            weak_topic_improvement=round(weak_improvement, 4),
            mock_score_improvement=round(mock_improvement, 4),
            plan_efficiency=round(efficiency, 4),
            proactive_bonus=round(proactive, 4),
            deadline_penalty=round(deadline_pen, 4),
            redundancy_penalty=round(redundancy_pen, 4),
            recovery_bonus=round(recovery, 4),
            breakdown={
                "coverage_delta":     round(coverage_delta, 4),
                "weak_improvement":   round(weak_improvement, 4),
                "mock_improvement":   round(mock_improvement, 4),
                "efficiency":         round(efficiency, 4),
                "proactive":          round(proactive, 4),
                "deadline_penalty":   round(deadline_pen, 4),
                "redundancy_penalty": round(redundancy_pen, 4),
                "recovery_bonus":     round(recovery, 4),
            },
            message=self._build_message(total, deadline_pen, weak_improvement, recovery),
        )

    def final_score(self, obs):
        weighted_coverage = sum(t.coverage() * t.weight for t in obs.topics)
        total_weight      = sum(t.weight for t in obs.topics)
        coverage_score    = weighted_coverage / total_weight if total_weight > 0 else 0.0

        mock_scores  = [r.overall_score for r in obs.recent_mock_results]
        mock_score   = max(mock_scores) if mock_scores else 0.0

        weak_topics     = [t for t in obs.topics if t.is_weak()]
        recovery_score  = 1.0 - (len(weak_topics) / max(len(obs.topics), 1))
        schedule_score  = max(0.0, 1.0 - (obs.days_behind_schedule / max(obs.total_days, 1)))

        final = (
            coverage_score   * 0.35
            + mock_score     * 0.35
            + recovery_score * 0.20
            + schedule_score * 0.10
        )
        return round(min(1.0, max(0.0, final)), 4)

    def _coverage_delta(self, before, after):
        return self._weighted_coverage(after.topics) - self._weighted_coverage(before.topics)

    def _weighted_coverage(self, topics):
        total_weight = sum(t.weight for t in topics)
        if total_weight == 0:
            return 0.0
        return sum(t.coverage() * t.weight for t in topics) / total_weight

    def _weak_topic_improvement(self, action, before, after):
        if action.action_type not in (ActionType.ALLOCATE_TIME, ActionType.BOOST_TOPIC):
            return 0.0
        weak_before = {t.name for t in before.topics if t.is_weak()}
        if action.topic_name not in weak_before:
            return 0.0
        t_before = next((t for t in before.topics if t.name == action.topic_name), None)
        t_after  = next((t for t in after.topics  if t.name == action.topic_name), None)
        if t_before and t_after:
            return t_after.coverage() - t_before.coverage()
        return 0.0

    def _mock_score_improvement(self, before, after):
        if not before.recent_mock_results or not after.recent_mock_results:
            return 0.0
        return max(0.0, after.recent_mock_results[-1].overall_score - before.recent_mock_results[-1].overall_score)

    def _plan_efficiency(self, action, obs):
        if action.action_type != ActionType.ALLOCATE_TIME or not action.hours:
            return 0.0
        if action.hours <= obs.student.hours_per_day:
            return 0.5
        return max(0.0, 0.5 - (action.hours - obs.student.hours_per_day) * 0.1)

    def _proactive_bonus(self, action, obs):
        if action.action_type == ActionType.SCHEDULE_MOCK:
            days_ahead = (action.day_target or obs.day) - obs.day
            if days_ahead >= 7:
                return 1.0
            elif days_ahead >= 3:
                return 0.5
        if action.action_type == ActionType.BOOST_TOPIC:
            next_mock = next(
                (d for d in sorted(obs.current_plan.mock_test_days) if d > obs.day), None
            ) if obs.current_plan else None
            if next_mock and (next_mock - obs.day) >= 5:
                return 0.8
        return 0.0

    def _deadline_penalty(self, obs):
        if obs.days_behind_schedule <= 0:
            return 0.0
        severity = obs.days_behind_schedule / max(obs.total_days, 1)
        return self.DEADLINE_PENALTY * min(severity * 3, 1.0)

    def _redundancy_penalty(self, action, obs):
        if action.action_type != ActionType.ALLOCATE_TIME or not action.topic_name:
            return 0.0
        topic = next((t for t in obs.topics if t.name == action.topic_name), None)
        if topic and topic.coverage() > 0.85 and not topic.is_weak():
            return self.REDUNDANCY_PENALTY
        return 0.0

    def _recovery_bonus(self, before, after):
        if not before.recent_mock_results:
            return 0.0
        if before.recent_mock_results[-1].overall_score >= 0.5:
            return 0.0
        if after.overall_coverage > before.overall_coverage + 0.03:
            return self.RECOVERY_BONUS
        return 0.0

    def _build_message(self, total, deadline_pen, weak_improvement, recovery):
        if total > 0.5:
            return "Excellent decision — on track."
        if deadline_pen < -0.15:
            return "Warning: falling behind schedule. Replan immediately."
        if weak_improvement > 0.1:
            return "Good — addressing weak topics effectively."
        if recovery > 0:
            return "Recovery in progress — keep focused on weak areas."
        if total < 0:
            return "Suboptimal action — reconsider priorities."
        return "Steady progress."