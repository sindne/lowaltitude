import json
import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TERM_DB_PATH = os.path.join(_PROJECT_ROOT, "evaluation", "domain_terms.json")
SECTION_HEADINGS = {
    "conclusion": "【风险评估结论】",
    "factor_analysis": "【主要风险因素分析】",
    "score_calculation": "【综合评分计算】",
    "sora_params": "【SORA技术参数】",
    "safety_advice": "【安全建议】",
    "important_notice": "【重要提醒】",
    "legal_consequences": "【法律后果】",
    "special_risk": "【特殊风险说明】",
}
RISK_FACTOR_NAMES = {
    "population": "人口密度风险",
    "air_traffic": "空域交通风险",
    "building": "建筑风险",
    "weather": "天气风险",
    "topology": "地理拓扑风险",
}
RISK_FACTOR_WEIGHT_LABELS = {
    "population": "权重0.416",
    "air_traffic": "权重0.262",
    "building": "权重0.161",
    "weather": "权重0.098",
    "topology": "权重0.063",
}
RISK_LEVEL_LABELS = {
    "低风险": "低风险（风险分数：0.00-0.20）",
    "较低风险": "较低风险（风险分数：0.20-0.40）",
    "中等风险": "中等风险（风险分数：0.40-0.60）",
    "较高风险": "较高风险（风险分数：0.60-0.80）",
    "极高风险": "极高风险（风险分数：0.80-1.00）",
}
SORA_PARAM_TEMPLATES = {
    "III": {"grc": "3", "arc": "b"},
    "IV": {"grc": "4", "arc": "c"},
    "V": {"grc": "5", "arc": "d"},
    "VI": {"grc": "5", "arc": "d"},
}
RISK_DEGREE_TERMS = {
    "low": ["低", "稀疏", "较少", "平坦", "温和", "偏低"],
    "medium": ["中等", "适中", "一般", "偶有", "局部"],
    "high": ["高", "密集", "频繁", "复杂", "显著", "高度"],
    "extreme": ["极高", "极度", "严重", "极低"],
}
SIMILARITY_PHRASES = {
    "人口密度": ["人口密度", "人口密集", "人员密集", "常住人口密度", "人员高度密集", "人口密度约"],
    "空域交通": ["空中交通", "空域交通", "航线覆盖", "空中冲突", "航线密集", "航班超"],
    "建筑": ["建筑", "高楼", "高层建筑", "建筑密集", "地标建筑", "建筑高度"],
    "天气": ["气候", "天气", "气象", "风速", "台风", "狂风", "强对流", "雷暴", "季风"],
    "地理拓扑": ["地形", "地势", "地理", "拓扑", "海拔", "山地", "盆地", "地形复杂"],
}
class DomainTerminology:
    def __init__(self):
        self._terms = self._load_terms()
        self._phrases = self._build_phrase_map()
    def _load_terms(self) -> dict:
        if os.path.exists(_TERM_DB_PATH):
            with open(_TERM_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    def _build_phrase_map(self) -> dict:
        pmap = {}
        for domain, phrases in SIMILARITY_PHRASES.items():
            for phrase in phrases:
                pmap[phrase] = domain
        return pmap
    def get_risk_factor_text(self, factor_key: str, score: float,
                              description: str) -> str:
        name = RISK_FACTOR_NAMES.get(factor_key, factor_key)
        label = RISK_FACTOR_WEIGHT_LABELS.get(factor_key, "")
        return f"{name}（{label}）：{description}，评分{score:.2f}"
    def get_sora_line(self, sail: str) -> str:
        params = SORA_PARAM_TEMPLATES.get(sail, {"grc": "4", "arc": "c"})
        lines = [
            f"- 地面风险等级（GRC）：{params['grc']}",
            f"- 空中风险类别（ARC）：{params['arc']}",
            f"- 最终SAIL等级：{sail}",
        ]
        return "\n".join(lines)
    def get_safety_advice(self, risk_level: str, scenario: str) -> list:
        advice_map = {
            "低风险": [
                "可正常飞行，保持常规安全措施",
                "建议配置基础避障系统",
                "飞行前检查天气状况和设备状态",
            ],
            "较低风险": [
                "建议在常规安全措施基础上增加飞行前风险提示",
                "注意避开局部敏感区域",
                "建议配置气象实时监测设备",
            ],
            "中等风险": [
                "需谨慎飞行，建议降低飞行高度或绕行高风险区域",
                "飞行前需向相关部门报备",
                "避开人员密集时段和区域",
                "建议飞行高度控制在100m以下",
            ],
            "较高风险": [
                "需经审批后方可飞行，配备应急方案与实时监控",
                "保持距高层建筑200m以上安全距离",
                "必须在申报的飞行空域和时间内执行",
                "配备冗余导航和通信系统",
            ],
            "极高风险": [
                "建议禁止常规飞行，特殊情况需特别审批",
                "必须配备多重安全冗余系统",
                "需制定详细应急预案并报备",
                "飞行前须进行全面的安全风险评估",
                "配备实时监控和应急通信链路",
            ],
        }
        return advice_map.get(risk_level, ["需进一步评估后确定飞行许可"])
    def get_formula_text(self, pop_score, building_score, air_score,
                          weather_score, topo_score) -> str:
        return (
            f"综合风险分数 = {pop_score:.2f}×0.416 + {air_score:.2f}×0.262"
            f" + {building_score:.2f}×0.161 + {weather_score:.2f}×0.098"
            f" + {topo_score:.2f}×0.063 = {self._calc_score(pop_score, building_score, air_score, weather_score, topo_score):.2f}"
        )
    @staticmethod
    def _calc_score(p, b, a, w, t):
        return p * 0.416 + a * 0.262 + b * 0.161 + w * 0.098 + t * 0.063
_terminology_instance = None
def get_terminology() -> DomainTerminology:
    global _terminology_instance
    if _terminology_instance is None:
        _terminology_instance = DomainTerminology()
    return _terminology_instance