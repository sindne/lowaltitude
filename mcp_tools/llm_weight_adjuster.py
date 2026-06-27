import json
import re
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools.llm_risk_assessor import LLMRiskAssessor


class LLMWeightAdjuster:

    def __init__(self, local_llm_client=None):
        self._local_llm = local_llm_client
        self._adjustment_history: List[Dict] = []

        self.city_feature_templates = {
            "超大城市": {
                "population_density_threshold": 8000,
                "building_density_threshold": 0.7,
                "adjustment_rules": {
                    "人口密度": 1.05, "空中交通": 1.03,
                    "建筑物密度": 1.02, "天气条件": 0.98, "地理拓扑": 0.97
                }
            },
            "大城市": {
                "population_density_threshold": 5000,
                "building_density_threshold": 0.5,
                "adjustment_rules": {
                    "人口密度": 1.03, "空中交通": 1.02,
                    "建筑物密度": 1.02, "天气条件": 1.0, "地理拓扑": 1.0
                }
            },
            "中等城市": {
                "population_density_threshold": 2000,
                "building_density_threshold": 0.3,
                "adjustment_rules": {
                    "人口密度": 1.0, "空中交通": 1.0,
                    "建筑物密度": 1.0, "天气条件": 1.0, "地理拓扑": 1.0
                }
            },
            "小城市": {
                "population_density_threshold": 1000,
                "building_density_threshold": 0.2,
                "adjustment_rules": {
                    "人口密度": 0.97, "空中交通": 0.98,
                    "建筑物密度": 0.98, "天气条件": 1.02, "地理拓扑": 1.03
                }
            }
        }

    @property
    def local_llm_available(self) -> bool:
        if self._local_llm is None:
            from knowledge_graph.local_llm_client import get_local_llm
            self._local_llm = get_local_llm()
        if not self._local_llm.available:
            self._local_llm._check_availability()
        return self._local_llm.available

    def set_local_llm(self, client):
        self._local_llm = client

    def adjust_weights_by_llm(
        self,
        base_weights: Dict[str, float],
        city_data: Dict[str, Any]
    ) -> Dict[str, float]:
        adjusted = None
        method = "rule_based"

        if self.local_llm_available:
            try:
                adjusted = self._adjust_with_local_llm(base_weights, city_data)
                if adjusted and self._validate_weight_order(adjusted):
                    method = "local_llm"
                    print(f"[权重调整] 本地LLM调整成功 (method={method})")
            except Exception as e:
                print(f"[权重调整] 本地LLM调整失败: {e}，回退到规则引擎")

        if adjusted is None:
            adjusted = self._adjust_with_rules(base_weights, city_data)
            print(f"[权重调整] 使用规则引擎 (method={method})")

        self._adjustment_history.append({
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "city_data_keys": list(city_data.keys()),
            "base_weights": dict(base_weights),
            "adjusted_weights": dict(adjusted)
        })

        return adjusted

    def _adjust_with_local_llm(
        self,
        base_weights: Dict[str, float],
        city_data: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        system_prompt = (
            "你是一位低空空域风险评估与AHP多准则决策专家。"
            "你的任务是根据城市的多维度特征数据，对预设的AHP基础权重进行微调。\n\n"
            "核心约束：\n"
            "1. 保持权重排序不变：人口密度 > 空中交通 > 建筑物密度 > 天气条件 > 地理拓扑\n"
            "2. 每个权重的调整幅度控制在 ±5% 以内（即调整系数在 0.95～1.05 之间）\n"
            "3. 调整后所有权重之和必须等于 1.0\n"
            "4. 调整需有明确的理论依据，基于城市特征数据分析\n\n"
            "分析维度：\n"
            "- 人口密度越高 → 人口密度权重适当上调（事故后果严重性增加）\n"
            "- 机场数量多、空中交通繁忙 → 空中交通权重适当上调（碰撞风险增加）\n"
            "- 建筑密度高、超高层建筑多 → 建筑物权重适当上调（障碍物风险增加）\n"
            "- 风速高、有台风影响 → 天气条件权重适当上调（环境不确定性增加）\n"
            "- 敏感设施密集 → 地理拓扑权重适当上调（空域管控风险增加）\n\n"
            "输出必须为严格的 JSON 格式，不包含任何其他文本：\n"
            '{"adjustment_factors": {"人口密度": 1.03, "空中交通": 1.02, "建筑物密度": 1.01, "天气条件": 1.00, "地理拓扑": 0.98}, "analysis": "简要分析说明"}'
        )

        user_prompt = f"""请根据以下城市特征数据，对AHP基础权重进行微调。

【AHP基础权重】
{json.dumps(base_weights, ensure_ascii=False, indent=2)}

【城市特征数据】
- 人口密度: {city_data.get('population_density', 'N/A')} 人/km²
- 建筑密度: {city_data.get('building_density', 'N/A')}
- 机场数量: {city_data.get('num_airports', 'N/A')} 个
- 平均风速: {city_data.get('avg_wind_speed', 'N/A')} m/s
- 地理拓扑评分: {city_data.get('geo_topology_score', 'N/A')}
- 有台风影响: {city_data.get('has_typhoon', 'N/A')}
- 有敏感设施: {city_data.get('has_sensitive_facilities', 'N/A')}
- 城市区域面积: {city_data.get('area_km2', 'N/A')} km²
- 年飞行量(架次): {city_data.get('annual_flights', 'N/A')}

请输出 JSON 格式的调整系数。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            result = self._local_llm.chat(messages, temperature=0.2, max_tokens=512)
            if not result or 'choices' not in result:
                return None

            content = result['choices'][0]['message']['content'].strip()
            print(f"[权重调整] 本地LLM原始输出: {content[:200]}...")

            parsed = self._parse_adjustment_json(content)
            if not parsed or 'adjustment_factors' not in parsed:
                return None

            factors = parsed['adjustment_factors']
            adjusted = {}
            for criterion in base_weights:
                factor = factors.get(criterion, 1.0)
                factor = max(0.95, min(1.05, float(factor)))
                adjusted[criterion] = base_weights[criterion] * factor

            total = sum(adjusted.values())
            for key in adjusted:
                adjusted[key] = round(adjusted[key] / total, 3)

            return adjusted

        except Exception as e:
            print(f"[权重调整] 本地LLM调用异常: {e}")
            return None

    def _parse_adjustment_json(self, content: str) -> Optional[Dict]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        print(f"[权重调整] 无法解析LLM输出为JSON")
        return None

    def _adjust_with_rules(self, base_weights: Dict[str, float], city_data: Dict[str, Any]) -> Dict[str, float]:
        city_type = self._classify_city_type(city_data)
        rules = self.city_feature_templates[city_type]["adjustment_rules"]

        adjusted = {}
        for criterion, base_weight in base_weights.items():
            rule_factor = rules.get(criterion, 1.0)
            custom_factor = self._calculate_custom_adjustment(criterion, city_data)
            final_factor = (rule_factor + custom_factor) / 2.0
            adjusted[criterion] = base_weight * final_factor

        total = sum(adjusted.values())
        for key in adjusted:
            adjusted[key] = round(adjusted[key] / total, 3)

        if not self._validate_weight_order(adjusted):
            adjusted = self._conservative_adjustment(base_weights, city_data)

        return adjusted

    def _validate_weight_order(self, weights: Dict[str, float]) -> bool:
        try:
            return (weights['人口密度'] > weights['空中交通'] >
                    weights['建筑物密度'] > weights['天气条件'] >
                    weights['地理拓扑'])
        except KeyError:
            return False

    def _conservative_adjustment(self, base_weights: Dict[str, float], city_data: Dict[str, Any]) -> Dict[str, float]:
        adjusted = base_weights.copy()
        pop_density = city_data.get('population_density', 2000)
        building_density = city_data.get('building_density', 0.5)
        num_airports = city_data.get('num_airports', 1)
        wind_speed = city_data.get('avg_wind_speed', 5.0)
        geo_topology = city_data.get('geo_topology_score', 0.5)

        pop_factor = min(1.03, max(0.97, pop_density / 5000.0 * 0.06 + 0.97))
        building_factor = min(1.03, max(0.97, building_density / 0.5 * 0.06 + 0.97))
        air_traffic_factor = min(1.03, max(0.97, num_airports / 2.0 * 0.06 + 0.97))
        weather_factor = min(1.03, max(0.97, wind_speed / 5.0 * 0.06 + 0.97))
        geo_factor = min(1.03, max(0.97, geo_topology / 0.5 * 0.06 + 0.97))

        adjusted['人口密度'] *= pop_factor
        adjusted['空中交通'] *= air_traffic_factor
        adjusted['建筑物密度'] *= building_factor
        adjusted['天气条件'] *= weather_factor
        adjusted['地理拓扑'] *= geo_factor

        total = sum(adjusted.values())
        for key in adjusted:
            adjusted[key] = round(adjusted[key] / total, 3)

        return adjusted

    def _classify_city_type(self, city_data: Dict[str, Any]) -> str:
        pop_density = city_data.get('population_density', 2000)
        building_density = city_data.get('building_density', 0.5)
        if pop_density >= 8000 and building_density >= 0.7:
            return "超大城市"
        elif pop_density >= 5000 and building_density >= 0.5:
            return "大城市"
        elif pop_density >= 2000 and building_density >= 0.3:
            return "中等城市"
        else:
            return "小城市"

    def _calculate_custom_adjustment(self, criterion: str, city_data: Dict[str, Any]) -> float:
        if criterion == "人口密度":
            pop = city_data.get('population_density', 2000)
            if pop > 10000: return 1.05
            elif pop > 5000: return 1.03
            elif pop > 2000: return 1.0
            else: return 0.98
        elif criterion == "建筑物密度":
            building = city_data.get('building_density', 0.5)
            if building > 0.8: return 1.04
            elif building > 0.6: return 1.02
            elif building > 0.4: return 1.0
            else: return 0.98
        elif criterion == "空中交通":
            airports = city_data.get('num_airports', 1)
            if airports >= 3: return 1.05
            elif airports >= 2: return 1.03
            elif airports >= 1: return 1.0
            else: return 0.98
        elif criterion == "天气条件":
            wind = city_data.get('avg_wind_speed', 5.0)
            typhoon = city_data.get('has_typhoon', False)
            if typhoon or wind > 10: return 1.04
            elif wind > 8: return 1.02
            elif wind > 5: return 1.0
            else: return 0.98
        elif criterion == "地理拓扑":
            geo = city_data.get('geo_topology_score', 0.5)
            has_sensitive = city_data.get('has_sensitive_facilities', False)
            if has_sensitive or geo > 0.7: return 1.04
            elif geo > 0.5: return 1.02
            elif geo > 0.3: return 1.0
            else: return 0.98
        return 1.0

    def generate_weight_report(
        self,
        base_weights: Dict[str, float],
        adjusted_weights: Dict[str, float],
        city_data: Dict[str, Any],
        adjustment_method: str = "rule_based"
    ) -> str:
        if self.local_llm_available:
            try:
                return self._generate_report_with_local_llm(
                    base_weights, adjusted_weights, city_data, adjustment_method
                )
            except Exception as e:
                print(f"[权重报告] 本地LLM报告生成失败: {e}")

        return self._generate_report_with_rules(base_weights, adjusted_weights, city_data)

    def _generate_report_with_local_llm(
        self,
        base_weights: Dict[str, float],
        adjusted_weights: Dict[str, float],
        city_data: Dict[str, Any],
        method: str
    ) -> str:
        changes = []
        for criterion in ["人口密度", "空中交通", "建筑物密度", "天气条件", "地理拓扑"]:
            base = base_weights.get(criterion, 0)
            adj = adjusted_weights.get(criterion, 0)
            change = ((adj - base) / base * 100) if base > 0 else 0
            direction = "上调" if change > 0.01 else "下调" if change < -0.01 else "不变"
            changes.append(f"{criterion}: {base*100:.1f}% → {adj*100:.1f}% ({direction}{abs(change):.1f}%)")

        system_prompt = (
            "你是低空空域风险评估专家，擅长AHP层次分析法权重解释。"
            "请生成专业的权重调整分析报告，内容需包含：调整原理、各因素变化分析、城市特征影响、地理拓扑说明。"
            "使用中文，语言专业但易读。"
        )

        user_prompt = f"""请为以下权重调整生成分析报告。

【调整方法】{method}
【城市特征】
- 人口密度: {city_data.get('population_density', 'N/A')} 人/km²
- 建筑密度: {city_data.get('building_density', 'N/A')}
- 机场数量: {city_data.get('num_airports', 'N/A')} 个
- 平均风速: {city_data.get('avg_wind_speed', 'N/A')} m/s
- 地理拓扑评分: {city_data.get('geo_topology_score', 'N/A')}
- 台风影响: {city_data.get('has_typhoon', 'N/A')}
- 敏感设施: {city_data.get('has_sensitive_facilities', 'N/A')}
- 区域面积: {city_data.get('area_km2', 'N/A')} km²

【权重变化】
{chr(10).join(changes)}

请生成完整的权重调整分析报告。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        result = self._local_llm.chat(messages, temperature=0.3, max_tokens=1024)
        if result and 'choices' in result:
            llm_report = LLMRiskAssessor.clean_report_text(
                result['choices'][0]['message']['content'].strip()
            )
            header = f"【权重调整分析报告】\n{'=' * 50}\n调整方法: {method}\n调整时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'=' * 50}\n\n"
            return header + llm_report

        return self._generate_report_with_rules(base_weights, adjusted_weights, city_data)

    def _generate_report_with_rules(
        self,
        base_weights: Dict[str, float],
        adjusted_weights: Dict[str, float],
        city_data: Dict[str, Any]
    ) -> str:
        city_type = self._classify_city_type(city_data)
        report = f"【权重调整分析报告】\n"
        report += f"{'=' * 60}\n"
        report += f"城市类型: {city_type}\n"
        report += f"调整时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        report += "一、调整原理\n"
        report += "基于AHP层次分析法的Saaty判断矩阵确定基础权重，"
        report += "结合城市多维特征数据进行规则化微调。"
        report += "调整遵循排序不变原则（±5%范围内），确保理论基础一致性。\n\n"

        report += "二、各因素调整详情\n"
        for criterion in ["人口密度", "空中交通", "建筑物密度", "天气条件", "地理拓扑"]:
            base = base_weights.get(criterion, 0)
            adjusted = adjusted_weights.get(criterion, 0)
            change = ((adjusted - base) / base * 100) if base > 0 else 0
            direction = "↑" if change > 0 else "↓" if change < 0 else "-"
            report += f"\n  {criterion}: {base:.3f}→{adjusted:.3f} {direction}{abs(change):.1f}%\n"

        report += "\n三、城市特征影响分析\n"
        report += f"  人口密度: {city_data.get('population_density', 'N/A')} 人/km²\n"
        report += f"  建筑密度: {city_data.get('building_density', 'N/A')}\n"
        report += f"  机场数量: {city_data.get('num_airports', 'N/A')}\n"
        report += f"  平均风速: {city_data.get('avg_wind_speed', 'N/A')} m/s\n"
        report += f"  地理拓扑评分: {city_data.get('geo_topology_score', 'N/A')}\n"

        report += "\n四、地理拓扑因素说明\n"
        report += "地理拓扑因素评估飞行航线与周边重要设施的空间关系：\n"
        report += "1. 以市中心为原点建立径向距离测算模型\n"
        report += "2. 计算飞行航线到各敏感设施（机场、政府、军事设施等）的最近距离\n"
        report += "3. 航路进入安全距离范围内时，根据设施类型和距离进行风险加权\n"
        report += "4. 加权公式: 风险加分 = 基础权重 × (1 - 实际距离/安全距离)\n"
        report += f"{'=' * 60}\n"

        return report


_llm_adjuster = None


def get_llm_weight_adjuster(local_llm_client=None) -> LLMWeightAdjuster:
    global _llm_adjuster
    if _llm_adjuster is None:
        _llm_adjuster = LLMWeightAdjuster(local_llm_client=local_llm_client)
    elif local_llm_client is not None:
        _llm_adjuster.set_local_llm(local_llm_client)
    return _llm_adjuster