"""
训练数据生成器
"""
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class TrainingDataGenerator:
    """训练数据生成器"""

    def __init__(self, output_path: str = "./training/data"):
        self.output_path = output_path
        self._ensure_output_path()

    def _ensure_output_path(self):
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path, exist_ok=True)

    def generate_risk_assessment_case(
        self,
        region: str,
        risk_level: str,
        factors: List[Dict[str, Any]],
        explanation: str,
        weather_data: Optional[Dict[str, Any]] = None,
        traffic_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        case = {
            "id": f"case_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": "risk_assessment",
            "region": region,
            "risk_level": risk_level,
            "factors": factors,
            "explanation": explanation,
            "weather_data": weather_data,
            "traffic_data": traffic_data,
            "created_at": datetime.now().isoformat(),
            "source": "generated"
        }
        return case

    def generate_conversation_pair(
        self,
        user_query: str,
        assistant_response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "id": f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": "conversation",
            "messages": [
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": assistant_response}
            ],
            "context": context,
            "created_at": datetime.now().isoformat()
        }

    def save_training_data(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        if filename is None:
            filename = f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = os.path.join(self.output_path, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return file_path

    def load_training_data(self, filename: str) -> List[Dict[str, Any]]:
        file_path = os.path.join(self.output_path, filename)
        if not os.path.exists(file_path):
            return []
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def merge_training_data(self, files: List[str], output_filename: Optional[str] = None) -> str:
        all_data = []
        for filename in files:
            data = self.load_training_data(filename)
            all_data.extend(data)
        return self.save_training_data(all_data, output_filename)

    def get_data_statistics(self, filename: str) -> Dict[str, Any]:
        data = self.load_training_data(filename)
        type_counts = {}
        risk_level_counts = {}
        for item in data:
            item_type = item.get('type', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            if item_type == 'risk_assessment':
                risk_level = item.get('risk_level', 'unknown')
                risk_level_counts[risk_level] = risk_level_counts.get(risk_level, 0) + 1
        return {
            "total_samples": len(data),
            "samples_by_type": type_counts,
            "risk_level_distribution": risk_level_counts
        }
