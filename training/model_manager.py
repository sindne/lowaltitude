"""
模型版本管理器
"""
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime


class ModelManager:
    """模型版本管理器"""
    
    def __init__(self, model_storage_path: str = "./training/models"):
        self.model_storage_path = model_storage_path
        self._ensure_storage_path()
        self.current_model: Optional[str] = None
    
    def _ensure_storage_path(self):
        if not os.path.exists(self.model_storage_path):
            os.makedirs(self.model_storage_path, exist_ok=True)
    
    def register_model(
        self,
        model_name: str,
        model_path: str,
        model_type: str = "lora",
        base_model: str = "deepseek-chat",
        description: str = "",
        metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        model_info = {
            "name": model_name,
            "path": model_path,
            "type": model_type,
            "base_model": base_model,
            "description": description,
            "metrics": metrics or {},
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        info_path = os.path.join(model_path, "model_info.json")
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, ensure_ascii=False, indent=2)
        
        return model_name
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        model_path = os.path.join(self.model_storage_path, model_name)
        info_path = os.path.join(model_path, "model_info.json")
        
        if not os.path.exists(info_path):
            return None
        
        with open(info_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_models(self) -> List[Dict[str, Any]]:
        models = []
        
        if not os.path.exists(self.model_storage_path):
            return models
        
        for item in os.listdir(self.model_storage_path):
            item_path = os.path.join(self.model_storage_path, item)
            if os.path.isdir(item_path):
                model_info = self.get_model_info(item)
                if model_info:
                    models.append(model_info)
        
        return sorted(models, key=lambda x: x["created_at"], reverse=True)
    
    def set_current_model(self, model_name: str) -> bool:
        model_info = self.get_model_info(model_name)
        if model_info:
            self.current_model = model_name
            return True
        return False
    
    def get_current_model(self) -> Optional[Dict[str, Any]]:
        if self.current_model:
            return self.get_model_info(self.current_model)
        return None
    
    def delete_model(self, model_name: str) -> bool:
        model_path = os.path.join(self.model_storage_path, model_name)
        
        if not os.path.exists(model_path):
            return False
        
        import shutil
        shutil.rmtree(model_path)
        
        if self.current_model == model_name:
            self.current_model = None
        
        return True
    
    def update_model_metrics(self, model_name: str, metrics: Dict[str, Any]) -> bool:
        model_info = self.get_model_info(model_name)
        if not model_info:
            return False
        
        model_info["metrics"].update(metrics)
        model_info["updated_at"] = datetime.now().isoformat()
        
        model_path = os.path.join(self.model_storage_path, model_name)
        info_path = os.path.join(model_path, "model_info.json")
        
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, ensure_ascii=False, indent=2)
        
        return True
