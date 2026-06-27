"""
训练与微调模块 - 基于 LLaMA Factory 的训练数据生成和LoRA微调
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.data_generator import TrainingDataGenerator
from training.simple_data_generator import SimpleTrainingDataGenerator
from training.lora_trainer import LoRATrainer, TrainingConfig

RealTrainingDataGenerator = SimpleTrainingDataGenerator


def get_real_data_generator():
    return SimpleTrainingDataGenerator()


class RealDatasetBuilder:
    """
    数据集构建器
    基于CHINA_CITY_DATA和数据库评估记录批量生成训练数据集
    """

    def __init__(self, db_path: str = "./data/risk_assessment.db", output_dir: str = "./training/data", postgis_db=None):
        self.db_path = db_path
        self.output_dir = output_dir
        self.postgis_db = postgis_db
        self._ensure_output_dir()
        self._simple_gen = SimpleTrainingDataGenerator(db_path=db_path)
        self._backend = TrainingDataGenerator(output_path=output_dir)

    def _ensure_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def _get_china_city_data(self):
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from main import CHINA_CITY_DATA
            return CHINA_CITY_DATA
        except Exception:
            return {}

    def generate_risk_assessment_dataset(self) -> list:
        cities = self._get_china_city_data()
        dataset = []

        for city_name, city_data in cities.items():
            case = self._backend.generate_risk_assessment_case(
                region=city_name,
                risk_level=city_data.get('default_risk_level', '中等风险'),
                factors=city_data.get('default_factors', ['人口密度', '建筑物密度']),
                explanation=f"{city_name}低空空域风险评估案例 - 人口密度{city_data.get('population_density', 'N/A')}人/km²"
            )
            if case:
                case['city_data'] = city_data
                dataset.append(case)

        db_data = self._simple_gen._get_data_from_db() if hasattr(self._simple_gen, '_get_data_from_db') else []
        for item in db_data:
            if not any(d.get('region') == item.get('region') for d in dataset):
                dataset.append(item)

        return dataset

    def save_dataset(self, dataset: list) -> str:
        filename = f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        return filepath

    def save_to_postgis(self, dataset: list = None, dataset_name: str = None, base_model: str = None) -> dict:
        if self.postgis_db is None:
            print("[RealDatasetBuilder] PostGIS 未连接，回退到文件存储")
            filepath = self.save_dataset(dataset)
            return {"file_path": filepath, "postgis_id": None}

        if dataset is None:
            dataset = self.generate_risk_assessment_dataset()

        if dataset_name is None:
            dataset_name = f"risk_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        dataset_id = self.postgis_db.create_training_dataset(
            name=dataset_name,
            dataset_type="risk_assessment",
            total_samples=len(dataset),
            base_model=base_model,
            metadata={"source": "RealDatasetBuilder", "city_count": len(set(d.get("region", "") for d in dataset))}
        )

        if dataset_id:
            count = self.postgis_db.add_training_samples_batch(dataset_id, dataset)
            print(f"[RealDatasetBuilder] 已存储 {count} 条训练数据到 PostGIS (dataset_id={dataset_id})")

        filepath = self.save_dataset(dataset)
        return {"file_path": filepath, "postgis_id": dataset_id, "sample_count": len(dataset)}

    def load_from_postgis(self, dataset_id: int = None, dataset_name: str = None, export_json: bool = True) -> list:
        if self.postgis_db is None:
            print("[RealDatasetBuilder] PostGIS 未连接")
            return []

        if dataset_id is None and dataset_name is None:
            latest = self.postgis_db.get_latest_training_dataset("risk_assessment")
            if latest:
                dataset_id = latest["id"]
            else:
                print("[RealDatasetBuilder] PostGIS 中无训练数据集")
                return []

        if dataset_id is None and dataset_name:
            ds = self.postgis_db.get_training_dataset(name=dataset_name)
            if ds:
                dataset_id = ds["id"]
            else:
                return []

        samples = self.postgis_db.get_training_samples(dataset_id)

        if export_json and samples:
            self.postgis_db.export_training_json(dataset_id, os.path.join(self.output_dir, f"postgis_dataset_{dataset_id}.json"))

        return samples


from training.model_manager import ModelManager

__all__ = [
    'TrainingDataGenerator',
    'SimpleTrainingDataGenerator',
    'RealTrainingDataGenerator',
    'get_real_data_generator',
    'RealDatasetBuilder',
    'LoRATrainer',
    'TrainingConfig',
    'ModelManager'
]