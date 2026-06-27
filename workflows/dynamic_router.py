from typing import Dict, Any, Optional, List, Callable
from enum import Enum

class RoutingDecision(Enum):
    USE_KNOWLEDGE_GRAPH = "use_knowledge_graph"
    USE_VECTOR_DB = "use_vector_db"
    USE_TOOLS = "use_tools"
    FAST_PATH = "fast_path"
    FULL_ANALYSIS = "full_analysis"

class DynamicRouter:
    def __init__(self):
        self.routing_rules: List[Dict[str, Any]] = []
        self.decision_history: List[Dict[str, Any]] = []

    def add_routing_rule(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], bool],
        decisions: List[RoutingDecision],
        priority: int = 0
    ):
        self.routing_rules.append({
            "name": name,
            "condition": condition,
            "decisions": decisions,
            "priority": priority
        })
        self.routing_rules.sort(key=lambda x: -x["priority"])

    def analyze_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        analysis = {
            "query_length": len(query),
            "has_region_name": self._detect_region_name(query),
            "has_weather_keywords": self._detect_weather_keywords(query),
            "has_traffic_keywords": self._detect_traffic_keywords(query),
            "complexity_score": self._calculate_complexity(query, context),
            "needs_detailed_analysis": self._needs_detailed_analysis(query, context)
        }
        return analysis

    def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        analysis = self.analyze_query(query, context)
        decisions = set()
        for rule in self.routing_rules:
            if rule["condition"]({**analysis, **context}):
                decisions.update(rule["decisions"])
        if not decisions:
            decisions = self._get_default_decisions(analysis)
        routing_result = {
            "decisions": list(decisions),
            "analysis": analysis,
            "execution_plan": self._generate_execution_plan(list(decisions), analysis)
        }
        self.decision_history.append({
            "query": query,
            "analysis": analysis,
            "result": routing_result,
            "timestamp": None
        })
        return routing_result

    def _detect_region_name(self, query: str) -> bool:
        region_keywords = ["区", "县", "市", "省", "镇", "街道", "北京", "上海", "广州", "深圳"]
        return any(keyword in query for keyword in region_keywords)

    def _detect_weather_keywords(self, query: str) -> bool:
        weather_keywords = ["天气", "气温", "风速", "能见度", "降水", "下雨", "大风", "雾"]
        return any(keyword in query for keyword in weather_keywords)

    def _detect_traffic_keywords(self, query: str) -> bool:
        traffic_keywords = ["交通", "机场", "航线", "航班", "高铁", "铁路", "拥堵"]
        return any(keyword in query for keyword in traffic_keywords)

    def _calculate_complexity(self, query: str, context: Dict[str, Any]) -> float:
        score = 0.0
        score += min(len(query) / 200, 0.5)
        score += 0.2 if self._detect_region_name(query) else 0
        score += 0.2 if self._detect_weather_keywords(query) else 0
        score += 0.2 if self._detect_traffic_keywords(query) else 0
        return min(score, 1.0)

    def _needs_detailed_analysis(self, query: str, context: Dict[str, Any]) -> bool:
        detailed_keywords = ["详细", "全面", "深入", "精确", "准确", "综合"]
        return any(keyword in query for keyword in detailed_keywords)

    def _get_default_decisions(self, analysis: Dict[str, Any]) -> List[RoutingDecision]:
        decisions = [RoutingDecision.USE_VECTOR_DB]
        if analysis["complexity_score"] > 0.5:
            decisions.append(RoutingDecision.USE_KNOWLEDGE_GRAPH)
        if analysis["has_region_name"] or analysis["has_weather_keywords"] or analysis["has_traffic_keywords"]:
            decisions.append(RoutingDecision.USE_TOOLS)
        if analysis["needs_detailed_analysis"]:
            decisions.append(RoutingDecision.FULL_ANALYSIS)
        else:
            decisions.append(RoutingDecision.FAST_PATH)
        return decisions

    def _generate_execution_plan(self, decisions: List[RoutingDecision], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        plan = []
        if RoutingDecision.USE_VECTOR_DB in decisions:
            plan.append({
                "step": "retrieve_vector_db",
                "description": "从向量数据库检索相关知识"
            })
        if RoutingDecision.USE_KNOWLEDGE_GRAPH in decisions:
            plan.append({
                "step": "query_knowledge_graph",
                "description": "查询知识图谱获取结构化信息"
            })
        if RoutingDecision.USE_TOOLS in decisions:
            plan.append({
                "step": "invoke_tools",
                "description": "调用相关工具获取实时数据"
            })
        if RoutingDecision.FULL_ANALYSIS in decisions:
            plan.append({
                "step": "full_analysis",
                "description": "执行全面深度分析"
            })
        else:
            plan.append({
                "step": "fast_analysis",
                "description": "执行快速分析"
            })
        plan.append({
            "step": "generate_result",
            "description": "生成最终评估结果"
        })
        return plan

    def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.decision_history[-limit:]
