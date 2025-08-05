"""
Human-in-the-Loop Validation Tools Module.

Provides tools for human validation and quality assessment of AI-generated content.
"""
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


@dataclass
class ValidationTask:
    """A task for human validation."""
    id: str
    task_type: str  # "quality_rating", "comparison", "error_detection", "improvement"
    content: Dict[str, Any]
    instructions: str
    created_at: datetime
    assigned_to: Optional[str] = None
    completed_at: Optional[datetime] = None
    response: Optional[Dict[str, Any]] = None
    time_spent_seconds: Optional[int] = None
    confidence: Optional[float] = None


@dataclass
class ValidationSession:
    """A human validation session."""
    id: str
    validator_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    tasks_completed: int = 0
    total_tasks: int = 0
    average_confidence: float = 0.0
    agreement_score: Optional[float] = None


class HumanValidationInterface:
    """Interface for human validation of AI-generated content."""
    
    def __init__(self):
        self.active_sessions: Dict[str, ValidationSession] = {}
        self.task_queue: List[ValidationTask] = []
        self.completed_tasks: List[ValidationTask] = []
        self.validator_profiles: Dict[str, Dict[str, Any]] = {}
    
    def create_quality_rating_task(
        self,
        content: Dict[str, Any],
        dimensions: List[str],
        validator_id: Optional[str] = None
    ) -> ValidationTask:
        """
        Create a quality rating task for human validation.
        
        Args:
            content: Content to rate
            dimensions: Quality dimensions to assess
            validator_id: Optional specific validator assignment
            
        Returns:
            ValidationTask ready for human review
        """
        task = ValidationTask(
            id=str(uuid4()),
            task_type="quality_rating",
            content=content,
            instructions=self._generate_rating_instructions(dimensions),
            created_at=datetime.utcnow(),
            assigned_to=validator_id
        )
        
        self.task_queue.append(task)
        return task
    
    def create_comparison_task(
        self,
        content_a: Dict[str, Any],
        content_b: Dict[str, Any],
        criteria: List[str],
        validator_id: Optional[str] = None
    ) -> ValidationTask:
        """
        Create a comparison task between two AI outputs.
        
        Args:
            content_a: First content to compare
            content_b: Second content to compare
            criteria: Comparison criteria
            validator_id: Optional specific validator assignment
            
        Returns:
            ValidationTask for comparison
        """
        task = ValidationTask(
            id=str(uuid4()),
            task_type="comparison",
            content={
                "option_a": content_a,
                "option_b": content_b,
                "criteria": criteria
            },
            instructions=self._generate_comparison_instructions(criteria),
            created_at=datetime.utcnow(),
            assigned_to=validator_id
        )
        
        self.task_queue.append(task)
        return task
    
    def create_error_detection_task(
        self,
        content: Dict[str, Any],
        error_types: List[str],
        validator_id: Optional[str] = None
    ) -> ValidationTask:
        """
        Create an error detection task.
        
        Args:
            content: Content to check for errors
            error_types: Types of errors to look for
            validator_id: Optional specific validator assignment
            
        Returns:
            ValidationTask for error detection
        """
        task = ValidationTask(
            id=str(uuid4()),
            task_type="error_detection",
            content=content,
            instructions=self._generate_error_detection_instructions(error_types),
            created_at=datetime.utcnow(),
            assigned_to=validator_id
        )
        
        self.task_queue.append(task)
        return task
    
    def start_validation_session(self, validator_id: str) -> ValidationSession:
        """Start a new validation session for a human validator."""
        session = ValidationSession(
            id=str(uuid4()),
            validator_id=validator_id,
            started_at=datetime.utcnow(),
            total_tasks=len([t for t in self.task_queue if t.assigned_to in [validator_id, None]])
        )
        
        self.active_sessions[session.id] = session
        return session
    
    def get_next_task(self, session_id: str) -> Optional[ValidationTask]:
        """Get the next task for a validation session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        validator_id = session.validator_id
        
        # Find next unassigned or assigned task
        for task in self.task_queue:
            if not task.completed_at and task.assigned_to in [validator_id, None]:
                task.assigned_to = validator_id
                return task
        
        return None
    
    def submit_task_response(
        self,
        task_id: str,
        response: Dict[str, Any],
        confidence: float,
        time_spent_seconds: int
    ) -> bool:
        """
        Submit a response for a validation task.
        
        Args:
            task_id: ID of the task
            response: Validator's response
            confidence: Validator's confidence (0-1)
            time_spent_seconds: Time spent on task
            
        Returns:
            Success status
        """
        # Find task
        task = None
        for t in self.task_queue:
            if t.id == task_id:
                task = t
                break
        
        if not task:
            return False
        
        # Update task
        task.completed_at = datetime.utcnow()
        task.response = response
        task.confidence = confidence
        task.time_spent_seconds = time_spent_seconds
        
        # Move to completed
        self.task_queue.remove(task)
        self.completed_tasks.append(task)
        
        # Update session stats
        for session in self.active_sessions.values():
            if session.validator_id == task.assigned_to:
                session.tasks_completed += 1
                # Update average confidence
                total_confidence = session.average_confidence * (session.tasks_completed - 1)
                session.average_confidence = (total_confidence + confidence) / session.tasks_completed
                break
        
        return True
    
    def end_validation_session(self, session_id: str) -> Optional[ValidationSession]:
        """End a validation session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        session.ended_at = datetime.utcnow()
        
        # Calculate agreement with other validators
        session.agreement_score = self._calculate_agreement_score(session.validator_id)
        
        # Update validator profile
        self._update_validator_profile(session)
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        return session
    
    def generate_validation_report(
        self,
        task_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a report of validation results.
        
        Args:
            task_ids: Specific task IDs to include (None for all)
            
        Returns:
            Comprehensive validation report
        """
        tasks = self.completed_tasks
        if task_ids:
            tasks = [t for t in tasks if t.id in task_ids]
        
        if not tasks:
            return {"error": "No completed tasks found"}
        
        # Aggregate results by task type
        results_by_type = {
            "quality_rating": self._aggregate_quality_ratings(tasks),
            "comparison": self._aggregate_comparisons(tasks),
            "error_detection": self._aggregate_error_detection(tasks),
        }
        
        # Calculate inter-rater reliability
        reliability = self._calculate_inter_rater_reliability(tasks)
        
        # Identify consensus issues
        consensus_issues = self._identify_consensus_issues(tasks)
        
        return {
            "summary": {
                "total_tasks": len(tasks),
                "validators": len(set(t.assigned_to for t in tasks if t.assigned_to)),
                "average_confidence": sum(t.confidence or 0 for t in tasks) / len(tasks),
                "average_time_seconds": sum(t.time_spent_seconds or 0 for t in tasks) / len(tasks),
            },
            "results_by_type": results_by_type,
            "inter_rater_reliability": reliability,
            "consensus_issues": consensus_issues,
            "validator_performance": self._analyze_validator_performance(tasks),
        }
    
    def _generate_rating_instructions(self, dimensions: List[str]) -> str:
        """Generate instructions for quality rating tasks."""
        dim_descriptions = {
            "coherence": "Logical flow and connection between ideas",
            "accuracy": "Factual correctness and precision",
            "completeness": "Coverage of all necessary information",
            "clarity": "Ease of understanding and readability",
            "academic_tone": "Appropriate academic language and style",
            "visual_appeal": "Visual organization and presentation",
        }
        
        instructions = "Please rate the following content on these dimensions:\n\n"
        
        for dim in dimensions:
            desc = dim_descriptions.get(dim, dim)
            instructions += f"- **{dim.title()}**: {desc}\n"
            instructions += "  Rate from 1 (Poor) to 5 (Excellent)\n\n"
        
        instructions += "\nProvide specific feedback for any ratings below 4."
        
        return instructions
    
    def _generate_comparison_instructions(self, criteria: List[str]) -> str:
        """Generate instructions for comparison tasks."""
        instructions = "Compare Option A and Option B based on the following criteria:\n\n"
        
        for criterion in criteria:
            instructions += f"- {criterion.title()}\n"
        
        instructions += "\nFor each criterion, indicate:\n"
        instructions += "- Which option is better (A, B, or Equal)\n"
        instructions += "- Brief justification for your choice\n"
        instructions += "\nFinally, select the overall better option."
        
        return instructions
    
    def _generate_error_detection_instructions(self, error_types: List[str]) -> str:
        """Generate instructions for error detection tasks."""
        error_descriptions = {
            "grammar": "Grammar, spelling, and punctuation errors",
            "factual": "Incorrect facts or misleading information",
            "citation": "Missing or incorrect citations",
            "formatting": "Formatting inconsistencies or issues",
            "logic": "Logical errors or contradictions",
            "technical": "Technical inaccuracies in specialized content",
        }
        
        instructions = "Please check for the following types of errors:\n\n"
        
        for error_type in error_types:
            desc = error_descriptions.get(error_type, error_type)
            instructions += f"- **{error_type.title()}**: {desc}\n"
        
        instructions += "\nFor each error found, provide:\n"
        instructions += "- Error location (slide/section)\n"
        instructions += "- Error description\n"
        instructions += "- Suggested correction\n"
        
        return instructions
    
    def _calculate_agreement_score(self, validator_id: str) -> float:
        """Calculate agreement score with other validators."""
        validator_tasks = [t for t in self.completed_tasks if t.assigned_to == validator_id]
        
        if not validator_tasks:
            return 0.0
        
        # Find tasks also completed by others
        agreement_scores = []
        
        for task in validator_tasks:
            # Find same content validated by others
            similar_tasks = [
                t for t in self.completed_tasks
                if t.id != task.id and t.content == task.content and t.assigned_to != validator_id
            ]
            
            if similar_tasks:
                # Calculate agreement
                agreement = self._calculate_task_agreement(task, similar_tasks)
                agreement_scores.append(agreement)
        
        return sum(agreement_scores) / len(agreement_scores) if agreement_scores else 0.0
    
    def _calculate_task_agreement(
        self,
        task: ValidationTask,
        similar_tasks: List[ValidationTask]
    ) -> float:
        """Calculate agreement between validators on a specific task."""
        if task.task_type == "quality_rating":
            # Compare ratings
            task_ratings = task.response.get("ratings", {})
            agreements = []
            
            for other_task in similar_tasks:
                other_ratings = other_task.response.get("ratings", {})
                
                # Calculate rating agreement
                common_dims = set(task_ratings.keys()) & set(other_ratings.keys())
                if common_dims:
                    diffs = [
                        abs(task_ratings[dim] - other_ratings[dim]) / 5.0
                        for dim in common_dims
                    ]
                    agreement = 1.0 - (sum(diffs) / len(diffs))
                    agreements.append(agreement)
            
            return sum(agreements) / len(agreements) if agreements else 0.0
        
        elif task.task_type == "comparison":
            # Compare choices
            agreements = []
            for other_task in similar_tasks:
                if task.response.get("overall_choice") == other_task.response.get("overall_choice"):
                    agreements.append(1.0)
                else:
                    agreements.append(0.0)
            
            return sum(agreements) / len(agreements) if agreements else 0.0
        
        return 0.0
    
    def _update_validator_profile(self, session: ValidationSession):
        """Update validator profile with session statistics."""
        validator_id = session.validator_id
        
        if validator_id not in self.validator_profiles:
            self.validator_profiles[validator_id] = {
                "total_sessions": 0,
                "total_tasks": 0,
                "average_confidence": 0.0,
                "average_agreement": 0.0,
                "total_time_seconds": 0,
            }
        
        profile = self.validator_profiles[validator_id]
        
        # Update statistics
        profile["total_sessions"] += 1
        profile["total_tasks"] += session.tasks_completed
        
        # Update averages
        if session.average_confidence > 0:
            total_conf = profile["average_confidence"] * (profile["total_sessions"] - 1)
            profile["average_confidence"] = (total_conf + session.average_confidence) / profile["total_sessions"]
        
        if session.agreement_score is not None:
            total_agree = profile["average_agreement"] * (profile["total_sessions"] - 1)
            profile["average_agreement"] = (total_agree + session.agreement_score) / profile["total_sessions"]
        
        # Calculate total time
        session_duration = (session.ended_at - session.started_at).total_seconds()
        profile["total_time_seconds"] += int(session_duration)
    
    def _aggregate_quality_ratings(self, tasks: List[ValidationTask]) -> Dict[str, Any]:
        """Aggregate quality rating results."""
        rating_tasks = [t for t in tasks if t.task_type == "quality_rating"]
        
        if not rating_tasks:
            return {}
        
        # Collect all ratings
        all_ratings = {}
        
        for task in rating_tasks:
            ratings = task.response.get("ratings", {})
            for dim, score in ratings.items():
                if dim not in all_ratings:
                    all_ratings[dim] = []
                all_ratings[dim].append(score)
        
        # Calculate statistics
        dimension_stats = {}
        for dim, scores in all_ratings.items():
            dimension_stats[dim] = {
                "mean": sum(scores) / len(scores),
                "std": np.std(scores) if len(scores) > 1 else 0,
                "min": min(scores),
                "max": max(scores),
                "count": len(scores),
            }
        
        return dimension_stats
    
    def _aggregate_comparisons(self, tasks: List[ValidationTask]) -> Dict[str, Any]:
        """Aggregate comparison task results."""
        comparison_tasks = [t for t in tasks if t.task_type == "comparison"]
        
        if not comparison_tasks:
            return {}
        
        # Count preferences
        preferences = {"A": 0, "B": 0, "Equal": 0}
        criteria_preferences = {}
        
        for task in comparison_tasks:
            overall = task.response.get("overall_choice", "")
            if overall in preferences:
                preferences[overall] += 1
            
            # Criteria-specific preferences
            criteria_choices = task.response.get("criteria_choices", {})
            for criterion, choice in criteria_choices.items():
                if criterion not in criteria_preferences:
                    criteria_preferences[criterion] = {"A": 0, "B": 0, "Equal": 0}
                if choice in criteria_preferences[criterion]:
                    criteria_preferences[criterion][choice] += 1
        
        return {
            "overall_preferences": preferences,
            "criteria_preferences": criteria_preferences,
            "total_comparisons": len(comparison_tasks),
        }
    
    def _aggregate_error_detection(self, tasks: List[ValidationTask]) -> Dict[str, Any]:
        """Aggregate error detection results."""
        error_tasks = [t for t in tasks if t.task_type == "error_detection"]
        
        if not error_tasks:
            return {}
        
        # Collect all errors
        error_counts = {}
        all_errors = []
        
        for task in error_tasks:
            errors = task.response.get("errors", [])
            all_errors.extend(errors)
            
            for error in errors:
                error_type = error.get("type", "unknown")
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_errors_found": len(all_errors),
            "error_counts_by_type": error_counts,
            "tasks_with_errors": sum(1 for t in error_tasks if t.response.get("errors")),
            "tasks_without_errors": sum(1 for t in error_tasks if not t.response.get("errors")),
        }
    
    def _calculate_inter_rater_reliability(self, tasks: List[ValidationTask]) -> Dict[str, float]:
        """Calculate inter-rater reliability metrics."""
        # Group tasks by content
        content_groups = {}
        
        for task in tasks:
            content_key = json.dumps(task.content, sort_keys=True)
            if content_key not in content_groups:
                content_groups[content_key] = []
            content_groups[content_key].append(task)
        
        # Calculate reliability for groups with multiple raters
        reliability_scores = []
        
        for content_key, group_tasks in content_groups.items():
            if len(group_tasks) > 1:
                # Calculate pairwise agreement
                agreements = []
                for i in range(len(group_tasks)):
                    for j in range(i + 1, len(group_tasks)):
                        agreement = self._calculate_task_agreement(
                            group_tasks[i], 
                            [group_tasks[j]]
                        )
                        agreements.append(agreement)
                
                if agreements:
                    reliability_scores.append(sum(agreements) / len(agreements))
        
        if reliability_scores:
            return {
                "average_agreement": sum(reliability_scores) / len(reliability_scores),
                "min_agreement": min(reliability_scores),
                "max_agreement": max(reliability_scores),
                "sample_size": len(reliability_scores),
            }
        
        return {"average_agreement": 0.0, "sample_size": 0}
    
    def _identify_consensus_issues(self, tasks: List[ValidationTask]) -> List[Dict[str, Any]]:
        """Identify issues where validators disagree."""
        # Group tasks by content
        content_groups = {}
        
        for task in tasks:
            content_key = json.dumps(task.content, sort_keys=True)
            if content_key not in content_groups:
                content_groups[content_key] = []
            content_groups[content_key].append(task)
        
        consensus_issues = []
        
        for content_key, group_tasks in content_groups.items():
            if len(group_tasks) > 1:
                # Check for disagreement
                if task.task_type == "quality_rating":
                    # Check rating variance
                    all_ratings = {}
                    for task in group_tasks:
                        ratings = task.response.get("ratings", {})
                        for dim, score in ratings.items():
                            if dim not in all_ratings:
                                all_ratings[dim] = []
                            all_ratings[dim].append(score)
                    
                    for dim, scores in all_ratings.items():
                        if len(scores) > 1:
                            variance = np.var(scores)
                            if variance > 1.0:  # High variance threshold
                                consensus_issues.append({
                                    "type": "rating_disagreement",
                                    "dimension": dim,
                                    "variance": variance,
                                    "scores": scores,
                                    "content_preview": str(group_tasks[0].content)[:100],
                                })
        
        return consensus_issues
    
    def _analyze_validator_performance(self, tasks: List[ValidationTask]) -> Dict[str, Any]:
        """Analyze individual validator performance."""
        validator_stats = {}
        
        for task in tasks:
            validator = task.assigned_to
            if validator:
                if validator not in validator_stats:
                    validator_stats[validator] = {
                        "tasks_completed": 0,
                        "average_confidence": 0.0,
                        "average_time": 0.0,
                        "agreement_scores": [],
                    }
                
                stats = validator_stats[validator]
                stats["tasks_completed"] += 1
                
                # Update averages
                if task.confidence:
                    total_conf = stats["average_confidence"] * (stats["tasks_completed"] - 1)
                    stats["average_confidence"] = (total_conf + task.confidence) / stats["tasks_completed"]
                
                if task.time_spent_seconds:
                    total_time = stats["average_time"] * (stats["tasks_completed"] - 1)
                    stats["average_time"] = (total_time + task.time_spent_seconds) / stats["tasks_completed"]
        
        return validator_stats