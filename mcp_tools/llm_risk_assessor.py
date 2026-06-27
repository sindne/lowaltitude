import json
import os
import re
import time
import sys
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

MARKDOWN_PATTERNS = [
    (re.compile(r'\*\*(.+?)\*\*'), r'\1'),     # **bold** → bold
    (re.compile(r'__([^_]+)__'), r'\1'),        # __bold__ → bold
    (re.compile(r'\*([^*]+)\*'), r'\1'),        # *italic* → italic
    (re.compile(r'_([^_]+)_'), r'\1'),          # _italic_ → italic
    (re.compile(r'#{1,6}\s*(.*)'), r'\1'),      # ### Heading → Heading
    (re.compile(r'`{1,3}([^`]+)`{1,3}'), r'\1'), # `code` → code
    (re.compile(r'~~(.+?)~~'), r'\1'),          # ~~strikethrough~~ → strikethrough
    (re.compile(r'^\s*>+\s?(.*)', re.M), r'\1'), # > blockquote
    (re.compile(r'^\s*[-*+]\s+(.*)', re.M), r'  \1'), # - list item
    (re.compile(r'^\s*\d+\.\s+(.*)', re.M), r'  \1'), # 1. numbered
    (re.compile(r'\[([^\]]+)\]\([^)]+\)'), r'\1'), # [text](url) → text
    (re.compile(r'!\[.*?\]\([^)]+\)'), ''),     # ![alt](url) → remove
]


class LLMRiskAssessor:

    def __init__(
        self,
        model_dir: str = "./training/local_models",
        api_key: str = None,
        local_llm_client=None
    ):
        self.model_dir = model_dir
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self._local_llm = local_llm_client
        self.available_models = self._scan_models()
        self.current_model = self._load_best_model()

    @property
    def local_llm_available(self) -> bool:
        if self._local_llm is None:
            from knowledge_graph.local_llm_client import get_local_llm
            self._local_llm = get_local_llm()
        if not self._local_llm.available:
            self._local_llm._check_availability()
        return self._local_llm.available

    @staticmethod
    def clean_report_text(text: str) -> str:
        for pattern, replacement in MARKDOWN_PATTERNS:
            text = pattern.sub(replacement, text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def set_local_llm(self, client):
        self._local_llm = client

    def _scan_models(self) -> List[Dict]:
        models = []
        if not os.path.exists(self.model_dir):
            return models
        for item in os.listdir(self.model_dir):
            item_path = os.path.join(self.model_dir, item)
            if os.path.isdir(item_path):
                status_file = os.path.join(item_path, "model_status.json")
                model_info = {
                    "name": item, "path": item_path,
                    "is_valid": False, "created_at": None,
                    "training_samples": 0, "has_training_data": False
                }
                if os.path.exists(status_file):
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status = json.load(f)
                        model_info["is_valid"] = status.get("is_valid", False)
                        model_info["created_at"] = status.get("created_at")
                        model_info["training_samples"] = status.get("num_training_samples", 0)
                models.append(model_info)
        return sorted(models, key=lambda x: x.get("created_at") or "", reverse=True)

    def _load_best_model(self) -> Optional[Dict]:
        valid_models = [m for m in self.available_models if m.get("is_valid")]
        if valid_models:
            return valid_models[0]
        return None

    def assess_risk_with_llm(
        self,
        region: str,
        sora_result: Dict,
        weighted_result: Dict,
        environmental_factors: Dict,
        city_real_data: Dict,
        weight_report: str = "",
        graph_context: Optional[Dict] = None
    ) -> Dict:
        local_provider = "template"

        if self.local_llm_available:
            try:
                print(f"[风险评估] 尝试本地LLM报告生成...")
                result = self._assess_with_local_llm(
                    region, sora_result, weighted_result,
                    environmental_factors, city_real_data,
                    weight_report, graph_context
                )
                if result and result.get("available"):
                    return result
            except Exception as e:
                print(f"[风险评估] 本地LLM失败: {e}")

        sora_score = sora_result.get('final_risk_score', 0.5)
        weighted_score = weighted_result.get('weighted_assessment', {}).get('weighted_score', 0.5)
        final_score = round(sora_score * 0.6 + weighted_score * 0.4, 4)
        risk_level = self._score_to_level(final_score)
        confidence = sora_result.get('confidence', {})
        auto_model_name = self.current_model.get("name", "本地大模型") if self.current_model else "本地大模型"

        template_report = self._generate_template_report(
            region, risk_level, final_score, sora_result, weighted_result
        )

        return {
            "available": True,
            "api_provider": local_provider,
            "llm_risk_score": final_score,
            "llm_risk_level": risk_level,
            "llm_correction": "SORA+AHP加权计算（本地大模型不可用）",
            "llm_analysis": "本地大模型服务不可用，采用SORA框架与AHP层次分析法加权计算生成评估报告。",
            "assessment_report": template_report,
            "inference_time_ms": 0,
            "api_response_valid": True,
            "llm_model_name": auto_model_name,
            "confidence": confidence
        }

    def _assess_with_local_llm(
        self,
        region: str,
        sora_result: Dict,
        weighted_result: Dict,
        environmental_factors: Dict,
        city_real_data: Dict,
        weight_report: str = "",
        graph_context: Optional[Dict] = None
    ) -> Dict:
        sora = sora_result.get('sora_assessment', {})
        weighted = weighted_result.get('weighted_assessment', {})

        system_prompt = (
            "你是低空空域风险评估高级专家。你需要基于JARUS SORA v2.0框架和AHP层次分析法，"
            "对目标区域无人机飞行风险进行综合评估，并生成专业、详实的评估报告。\n\n"
            "报告必须包含以下结构：\n"
            "1. 评估概要（风险等级、评分、核心结论）\n"
            "2. SORA框架分析（SAIL等级、地面/空中风险、动能分析）\n"
            "3. AHP多准则分析（人口、建筑、空交、天气、拓扑五项详细分析）\n"
            "4. 关键风险因素识别\n"
            "5. 飞行安全建议（按优先级排列）\n"
            "6. 风险缓解措施\n\n"
            "使用中文，语言专业但清晰易懂。用具体数据支撑分析结论。"
        )

        user_prompt = self._build_comprehensive_prompt(
            region, sora, weighted, environmental_factors,
            city_real_data, weight_report, graph_context
        )

        start_time = time.time()

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            result = self._local_llm.chat(messages, temperature=0.3, max_tokens=2048)

            if not result or 'choices' not in result:
                raise ValueError("本地LLM返回空结果")

            inference_time_ms = int((time.time() - start_time) * 1000)
            llm_output = self.clean_report_text(
                result['choices'][0]['message']['content'].strip()
            )

            sora_score = sora_result.get('final_risk_score', 0.5)
            weighted_score = weighted_result.get('weighted_assessment', {}).get('weighted_score', 0.5)
            confidence = sora_result.get('confidence', {})
            final_score = round(sora_score * 0.5 + weighted_score * 0.35 + 0.15, 3)
            final_score = max(0.0, min(1.0, final_score))
            risk_level = self._score_to_level(final_score)

            model_name = self.current_model.get("name", "本地大模型") if self.current_model else "本地大模型"

            report_header = (
                f"【{region}低空空域综合风险评估报告】\n"
                f"{'=' * 55}\n"
                f"评估框架: JARUS SORA v2.0 + AHP层次分析法\n"
                f"生成模型: 本地LoRA微调大模型\n"
                f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"综合风险等级: {risk_level} (评分: {final_score:.2f})\n"
                f"{'=' * 55}\n\n"
            )

            return {
                "available": True,
                "api_provider": "local_llm",
                "llm_risk_score": final_score,
                "llm_risk_level": risk_level,
                "llm_correction": "本地LoRA微调大模型综合评估",
                "llm_analysis": llm_output[:500],
                "assessment_report": report_header + llm_output,
                "inference_time_ms": inference_time_ms,
                "api_response_valid": True,
                "llm_model_name": self._local_llm.model_name if self._local_llm else model_name,
                "confidence": confidence
            }

        except Exception as e:
            print(f"[本地LLM评估] 失败: {e}")
            return {"available": False, "message": str(e), "fallback": "使用模板化报告回退"}

    def _assess_with_deepseek(
        self,
        region: str,
        sora_result: Dict,
        weighted_result: Dict,
        environmental_factors: Dict,
        city_real_data: Dict
    ) -> Dict:
        return {"available": False, "message": "DeepSeek已不在报告生成链路中使用"}

    def generate_comprehensive_report(
        self,
        region: str,
        sora_result: Dict,
        weighted_result: Dict,
        environmental_factors: Dict,
        city_real_data: Dict,
        weight_report: str = "",
        graph_context: Optional[Dict] = None
    ) -> str:
        assessment = self.assess_risk_with_llm(
            region, sora_result, weighted_result,
            environmental_factors, city_real_data,
            weight_report, graph_context
        )
        return assessment.get("assessment_report", "")

    def _build_comprehensive_prompt(
        self,
        region: str,
        sora: Dict,
        weighted: Dict,
        env_factors: Dict,
        city_data: Dict,
        weight_report: str,
        graph_context: Optional[Dict]
    ) -> str:
        prompt = f"请对【{region}】进行低空空域无人机飞行综合风险评估。\n\n"

        prompt += "一、SORA框架评估结果\n"
        prompt += f"- SAIL等级: {sora.get('sail_level', 'N/A')} (I-VI级)\n"
        prompt += f"- 地面风险等级: {sora.get('ground_risk_level', 'N/A')}\n"
        prompt += f"- 空中风险等级: {sora.get('air_risk_class', 'N/A')}\n"
        prompt += f"- 无人机动能等级: {sora.get('kinetic_energy_tier', 'N/A')}\n"
        prompt += f"- 无人机动能: {sora.get('drone_kinetic_energy_j', 400)}J\n"
        prompt += f"- 作业场景: {sora.get('operation_scenario', '标准视距内飞行')}\n\n"

        prompt += "二、AHP多准则加权评估\n"
        prompt += f"- 加权综合评分: {weighted.get('weighted_score', 0):.3f}\n"
        prompt += f"- 人口风险因子: {weighted.get('population_risk', 0):.3f}\n"
        prompt += f"- 建筑风险因子: {weighted.get('building_risk', 0):.3f}\n"
        prompt += f"- 空交风险因子: {weighted.get('air_traffic_risk', 0):.3f}\n"
        prompt += f"- 天气风险因子: {weighted.get('weather_risk', 0):.3f}\n"
        prompt += f"- 拓扑风险因子: {weighted.get('topology_risk', 0):.3f}\n"
        if weighted.get('weights'):
            prompt += "- 权重分配: " + ", ".join(
                f"{k}={v*100:.1f}%" for k, v in weighted['weights'].items()
            ) + "\n"
        prompt += "\n"

        prompt += "三、环境因子数据\n"
        if env_factors:
            for key, val in env_factors.items():
                if isinstance(val, dict):
                    prompt += f"- {key}: {json.dumps(val, ensure_ascii=False)}\n"
                else:
                    prompt += f"- {key}: {val}\n"
        prompt += "\n"

        prompt += "四、城市特征数据\n"
        prompt += f"- 人口密度: {city_data.get('population_density', 'N/A')} 人/km²\n"
        prompt += f"- 建筑密度: {city_data.get('building_density', 'N/A')}\n"
        prompt += f"- 机场数量: {city_data.get('num_airports', 'N/A')} 个\n"
        prompt += f"- 平均风速: {city_data.get('avg_wind_speed_ms', city_data.get('avg_wind_speed', 'N/A'))} m/s\n"
        prompt += f"- 台风影响: {city_data.get('has_typhoon', 'N/A')}\n"
        prompt += f"- 敏感设施: {city_data.get('has_sensitive_facilities', 'N/A')}\n"
        prompt += f"- 城市面积: {city_data.get('area_km2', 'N/A')} km²\n\n"

        if weight_report:
            prompt += "五、权重调整报告\n"
            prompt += weight_report[:1500] + "\n\n"

        if graph_context:
            prompt += "六、知识图谱上下文\n"
            summary = graph_context.get('summary', '')
            if summary:
                prompt += f"- 图谱摘要: {summary}\n"
            risk_factors = graph_context.get('risk_factors', [])
            if risk_factors:
                prompt += "- 风险因素: " + ", ".join(
                    f.get('name', '') for f in risk_factors[:5]
                ) + "\n"
            prompt += "\n"

        prompt += "请生成完整的综合风险评估报告，包含所有六个章节。"
        return prompt

    def _build_deepseek_prompt(
        self,
        region: str,
        sora_result: Dict,
        weighted_result: Dict,
        environmental_factors: Dict,
        city_real_data: Dict
    ) -> str:
        """构建DeepSeek API评估提示词"""
        sail = sora_result.get('sora_assessment', {})
        weighted = weighted_result.get('weighted_assessment', {})

        prompt = f"""对{region}进行低空空域风险评估分析：

SORA框架评估：
- SAIL等级: {sail.get('sail_level', 'N/A')}
- 地面风险等级: {sail.get('ground_risk_level', 'N/A')}
- 空中风险等级: {sail.get('air_risk_class', 'N/A')}
- 无人机动能: {sail.get('drone_kinetic_energy_j', 400)}J

AHP加权多准则评估：
- 加权风险分数: {weighted.get('weighted_score', 0)}
- 人口风险: {weighted.get('population_risk', 0)}
- 建筑风险: {weighted.get('building_risk', 0)}
- 空交风险: {weighted.get('air_traffic_risk', 0)}
- 天气风险: {weighted.get('weather_risk', 0)}
- 拓扑风险: {weighted.get('topology_risk', 0)}

城市特征：
- 人口密度: {city_real_data.get('population_density', 'N/A')}人/km²
- 建筑密度: {city_real_data.get('building_density', 'N/A')}
- 机场数量: {city_real_data.get('num_airports', 'N/A')}
- 平均风速: {city_real_data.get('avg_wind_speed_ms', 'N/A')}m/s

请分析该区域的低空飞行风险特征，给出评估结论和飞行建议。"""
        return prompt

    def _score_to_level(self, score: float) -> str:
        if score >= 0.8:
            return "极高风险"
        elif score >= 0.6:
            return "较高风险"
        elif score >= 0.4:
            return "中等风险"
        elif score >= 0.2:
            return "较低风险"
        else:
            return "低风险"

    def _generate_template_report(
        self,
        region: str,
        risk_level: str,
        score: float,
        sora_result: Dict,
        weighted_result: Dict
    ) -> str:
        sail = sora_result.get('sora_assessment', {})
        weighted = weighted_result.get('weighted_assessment', {})

        report = f"【{region}低空空域综合风险评估报告】\n"
        report += f"{'=' * 55}\n"
        report += f"评估框架: JARUS SORA v2.0 + AHP层次分析法\n"
        report += f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"综合风险等级: {risk_level} (评分: {score:.2f})\n"
        report += f"{'=' * 55}\n\n"

        report += "一、SORA框架分析\n"
        report += f"  SAIL等级: {sail.get('sail_level', 'N/A')}\n"
        report += f"  地面风险等级: {sail.get('ground_risk_level', 'N/A')}\n"
        report += f"  空中风险等级: {sail.get('air_risk_class', 'N/A')}\n"
        report += f"  动能: {sail.get('drone_kinetic_energy_j', 400)}J\n\n"

        report += "二、AHP多准则分析\n"
        report += f"  加权评分: {weighted.get('weighted_score', 0):.3f}\n"
        report += f"  人口风险: {weighted.get('population_risk', 0):.3f}\n"
        report += f"  建筑风险: {weighted.get('building_risk', 0):.3f}\n"
        report += f"  空交风险: {weighted.get('air_traffic_risk', 0):.3f}\n"
        report += f"  天气风险: {weighted.get('weather_risk', 0):.3f}\n"
        report += f"  拓扑风险: {weighted.get('topology_risk', 0):.3f}\n\n"

        report += "三、飞行建议\n"
        if risk_level == "低风险":
            report += "  可正常飞行，保持常规安全措施。\n"
        elif risk_level == "较低风险":
            report += "  建议在常规安全措施基础上增加飞行前风险提示。\n"
        elif risk_level == "中等风险":
            report += "  需谨慎飞行，建议降低飞行高度或绕行高风险区域。\n"
        elif risk_level == "较高风险":
            report += "  需经审批后方可飞行，配备应急方案与实时监控。\n"
        elif risk_level == "极高风险":
            report += "  建议禁止常规飞行，特殊情况需特别审批并配备多重安全冗余。\n"
        else:
            report += "  需进一步评估后确定飞行许可。\n"

        report += f"\n说明：此报告由SORA+AHP加权计算生成，LLM服务不可用。\n"
        report += f"{'=' * 55}\n"

        return report

    def get_model_info(self) -> Dict:
        info = {
            "local_llm_available": self.local_llm_available,
            "deepseek_api_configured": bool(self.api_key),
            "trained_models": len(self.available_models),
        }
        if self.current_model:
            info.update({
                "model_name": self.current_model.get("name"),
                "model_path": self.current_model.get("path"),
                "created_at": self.current_model.get("created_at"),
                "training_samples": self.current_model.get("training_samples"),
            })
        else:
            info["message"] = "无可用训练模型"
        return info

    def list_models(self) -> List[Dict]:
        return self.available_models


_llm_assessor_instance = None


def get_llm_risk_assessor(
    model_dir: str = None,
    api_key: str = None,
    local_llm_client=None
) -> LLMRiskAssessor:
    global _llm_assessor_instance
    if _llm_assessor_instance is None:
        _llm_assessor_instance = LLMRiskAssessor(
            model_dir=model_dir or "./training/local_models",
            api_key=api_key,
            local_llm_client=local_llm_client
        )
    elif local_llm_client is not None:
        _llm_assessor_instance.set_local_llm(local_llm_client)
    return _llm_assessor_instance