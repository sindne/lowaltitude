"""
简单训练数据生成器
"""
import json
import os
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime


class SimpleTrainingDataGenerator:
    """训练数据生成器"""

    def __init__(self, db_path: str = "./data/risk_assessment.db", output_path: str = "./training/data"):
        self.output_path = output_path
        self.db_path = db_path
        self._ensure_output_path()

    def _ensure_output_path(self):
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path, exist_ok=True)

    def _get_data_from_db(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return []
        db_data = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, region, risk_level, factors, explanation, created_at
                FROM assessments 
                ORDER BY created_at DESC 
                LIMIT 50
            ''')
            for row in cursor.fetchall():
                factors = json.loads(row[3]) if row[3] else []
                db_data.append({
                    'type': 'risk_assessment',
                    'region': row[1],
                    'risk_level': row[2],
                    'factors': factors,
                    'explanation': row[4],
                    'created_at': row[5],
                    'source': 'database'
                })
            conn.close()
            print(f"从SQLite数据库获取了 {len(db_data)} 条历史评估数据")
        except Exception as e:
            print(f"从SQLite数据库获取数据失败: {e}")
        return db_data

    def generate_risk_assessment_case(
        self,
        region: str,
        risk_level: str = "中等风险",
        factors: List[str] = None,
        explanation: str = ""
    ) -> Optional[Dict[str, Any]]:
        factors = factors or []
        try:
            case_id = f"case_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            case = {
                'id': case_id,
                'type': 'risk_assessment',
                'region': region,
                'risk_level': risk_level,
                'factors': factors,
                'explanation': explanation,
                'created_at': datetime.now().isoformat(),
                'source': 'generated'
            }
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO assessments (id, region, risk_level, factors, explanation)
                VALUES (?, ?, ?, ?, ?)
            ''', (case_id, region, risk_level, json.dumps(factors, ensure_ascii=False), explanation))
            conn.commit()
            conn.close()
            return case
        except Exception as e:
            print(f"生成评估案例失败: {e}")
            return None

    def generate_training_data(self, num_samples: int = 50) -> List[Dict[str, Any]]:
        all_data = []
        db_data = self._get_data_from_db()
        if db_data:
            all_data.extend(db_data)
            print(f"从数据库获取了 {len(db_data)} 条训练数据")
        if not all_data:
            print("数据库无评估记录，无法生成训练数据。请先执行评估操作。")
            return []
        final_data = []
        for item in all_data:
            conv = self._convert_to_conversation(item)
            if conv:
                final_data.append(conv)
        return final_data

    def _convert_to_conversation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            region = data.get('region', '该区域')
            risk_level = data.get('risk_level', '中等风险')
            factors = data.get('factors', []) or data.get('key_factors', [])
            user_query = f"请评估{region}的低空空域风险"
            if factors:
                factors_str = '、'.join(factors)
                assistant_response = f"{region}的低空空域风险等级为{risk_level}。主要风险因素包括：{factors_str}。"
            else:
                assistant_response = f"{region}的低空空域风险等级为{risk_level}。建议飞行前仔细核查空域限制，确保安全。"
            assistant_response += "如有具体飞行计划，可提供更精确的评估。"
            return {
                'id': f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                'type': 'conversation',
                'messages': [
                    {'role': 'user', 'content': user_query},
                    {'role': 'assistant', 'content': assistant_response}
                ],
                'source': data.get('source', 'generated'),
                'quality_score': 0.8 if data.get('source') == 'database' else 0.6
            }
        except Exception as e:
            print(f"转换对话格式失败: {e}")
            return None

    def save_data(self, data: List[Dict[str, Any]], filename: str = None) -> str:
        if filename is None:
            filename = f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = os.path.join(self.output_path, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return file_path

