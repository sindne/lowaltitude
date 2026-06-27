import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enum import Enum
from typing import Dict, Any, Optional
from workflows.base import BaseWorkflow, WorkflowStatus

class WorkflowMode(Enum):
    STANDARD = "standard"
    FAST = "fast"
    PRECISE = "precise"
    CUSTOM = "custom"

class MultiModeController:
    def __init__(self):
        self.workflows: Dict[WorkflowMode, BaseWorkflow] = {}
        self.current_mode: WorkflowMode = WorkflowMode.STANDARD
        self.mode_configs: Dict[WorkflowMode, Dict[str, Any]] = {
            WorkflowMode.STANDARD: {
                "description": "标准模式 - 平衡速度和精度",
                "max_tokens": 1500,
                "use_knowledge_graph": True,
                "use_vector_db": True
            },
            WorkflowMode.FAST: {
                "description": "快速模式 - 优先考虑响应速度",
                "max_tokens": 800,
                "use_knowledge_graph": False,
                "use_vector_db": False
            },
            WorkflowMode.PRECISE: {
                "description": "精确模式 - 优先考虑评估精度",
                "max_tokens": 2500,
                "use_knowledge_graph": True,
                "use_vector_db": True,
                "enhanced_analysis": True
            },
            WorkflowMode.CUSTOM: {
                "description": "自定义模式 - 用户自定义配置",
                "max_tokens": 1500,
                "use_knowledge_graph": True,
                "use_vector_db": True
            }
        }

    def register_workflow(self, mode: WorkflowMode, workflow: BaseWorkflow):
        self.workflows[mode] = workflow

    def set_mode(self, mode: WorkflowMode, config: Optional[Dict[str, Any]] = None):
        self.current_mode = mode
        if config and mode == WorkflowMode.CUSTOM:
            self.mode_configs[WorkflowMode.CUSTOM].update(config)

    def get_current_mode(self) -> WorkflowMode:
        return self.current_mode

    def get_mode_config(self, mode: Optional[WorkflowMode] = None) -> Dict[str, Any]:
        target_mode = mode or self.current_mode
        return self.mode_configs.get(target_mode, {})

    def execute(self, mode: Optional[WorkflowMode] = None, **kwargs) -> Dict[str, Any]:
        target_mode = mode or self.current_mode
        if target_mode not in self.workflows:
            raise ValueError(f"未注册的工作流模式: {target_mode}")
        workflow = self.workflows[target_mode]
        config = self.get_mode_config(target_mode)
        merged_kwargs = {**config, **kwargs}
        return workflow.execute(**merged_kwargs)

    def get_available_modes(self) -> Dict[WorkflowMode, Dict[str, Any]]:
        return {
            mode: config
            for mode, config in self.mode_configs.items()
            if mode in self.workflows
        }

    def auto_select_mode(self, query_complexity: float, urgency: float = 0.5) -> WorkflowMode:
        if urgency > 0.8:
            return WorkflowMode.FAST
        elif query_complexity > 0.7:
            return WorkflowMode.PRECISE
        else:
            return WorkflowMode.STANDARD
