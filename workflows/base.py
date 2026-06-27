from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class WorkflowStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class BaseWorkflow(ABC):
    def __init__(self, name: str):
        self.name = name
        self.status = WorkflowStatus.IDLE
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.context: Dict[str, Any] = {}

    @abstractmethod
    def _execute(self, **kwargs) -> Dict[str, Any]:
        pass

    def execute(self, **kwargs) -> Dict[str, Any]:
        self.status = WorkflowStatus.RUNNING
        self.context.update(kwargs)
        try:
            self.result = self._execute(**kwargs)
            self.status = WorkflowStatus.COMPLETED
            return self.result
        except Exception as e:
            self.error = str(e)
            self.status = WorkflowStatus.FAILED
            raise

    def get_status(self) -> WorkflowStatus:
        return self.status

    def get_result(self) -> Optional[Dict[str, Any]]:
        return self.result

    def get_error(self) -> Optional[str]:
        return self.error

    def reset(self):
        self.status = WorkflowStatus.IDLE
        self.result = None
        self.error = None
        self.context = {}
