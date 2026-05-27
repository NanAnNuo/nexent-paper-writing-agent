"""
Workflow DAG 引擎

管理论文写作流程的状态机。状态包括：
  initialized -> outline_generated -> writing_sections -> rendering -> completed

支持 while/if 控制流、重试、熔断。
"""

from enum import Enum
from typing import Optional, Callable

from .state_manager import PaperProject
from .circuit_breaker import CircuitBreaker
from core.utils import setup_logging

logger = setup_logging("workflow_engine")


class WorkflowState(str, Enum):
    INITIALIZED = "initialized"
    OUTLINE_GENERATED = "outline_generated"
    WRITING_SECTIONS = "writing_sections"
    SECTION_COMPLETED = "section_completed"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowEngine:
    """带状态的 Workflow 执行引擎"""

    def __init__(self, project: PaperProject):
        self.project = project
        self.state = WorkflowState(project.metadata.get("status", "initialized"))
        self._current_section_index = 0
        self._debug_breaker = CircuitBreaker(name="figure_debug", max_retries=3)
        self._review_breaker = CircuitBreaker(name="section_review", max_retries=3)

    def transition_to(self, new_state: WorkflowState):
        self.state = new_state
        self.project.metadata["status"] = new_state.value
        self.project.log_trace("state_transition", f"{self.state.value} -> {new_state.value}")
        logger.info(f"状态转换: {new_state.value}")

    @property
    def current_section_index(self) -> int:
        return self._current_section_index

    def set_section_index(self, index: int):
        self._current_section_index = index

    def advance_section(self):
        self._current_section_index += 1

    def get_remaining_sections(self, total_sections: int) -> list[int]:
        return list(range(self._current_section_index, total_sections))

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "current_section_index": self._current_section_index,
            "debug_breaker": self._debug_breaker.to_dict(),
            "review_breaker": self._review_breaker.to_dict(),
        }

    def load_from_dict(self, data: dict):
        self.state = WorkflowState(data.get("state", "initialized"))
        self._current_section_index = data.get("current_section_index", 0)
        if "debug_breaker" in data:
            self._debug_breaker = CircuitBreaker.from_dict(data["debug_breaker"])
        if "review_breaker" in data:
            self._review_breaker = CircuitBreaker.from_dict(data["review_breaker"])
