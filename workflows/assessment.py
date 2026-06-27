"""
风险评估工作流 - 集成 GraphRAG + LoRA 微调模型
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional
from workflows.base import BaseWorkflow, WorkflowStatus
from knowledge_graph.graph_rag import get_graph_rag, GraphRAG
from knowledge_graph.local_llm_client import get_local_llm, LocalLLMClient


class RiskAssessmentWorkflow(BaseWorkflow):
    """风险评估工作流 - 集成 GraphRAG 知识图谱检索和 LoRA 微调模型"""

    def __init__(
        self,
        graph_rag: Optional[GraphRAG] = None,
        llm_client: Optional[LocalLLMClient] = None,
        vector_retriever=None
    ):
        super().__init__("risk_assessment")
        self.graph_rag = graph_rag or get_graph_rag()
        self.llm_client = llm_client or get_local_llm()
        self.vector_retriever = vector_retriever

    def _execute(self, **kwargs) -> Dict[str, Any]:
        """执行风险评估工作流"""
        region = kwargs.get('region', '未知地区')
        use_knowledge_graph = kwargs.get('use_knowledge_graph', True)
        use_vector_db = kwargs.get('use_vector_db', True)
        use_llm = kwargs.get('use_llm', False)
        enhanced_analysis = kwargs.get('enhanced_analysis', False)
        user_query = kwargs.get('user_query', '')

        context = {
            "region": region,
            "knowledge_context": None,
            "vector_context": None,
            "llm_response": None,
            "engine": "memory"
        }

        if use_knowledge_graph:
            try:
                kg_context = self.graph_rag.get_context_for_report(region)
                context["knowledge_context"] = kg_context
                context["engine"] = kg_context.get("engine", "memory")
                self.context["graph_rag_context"] = kg_context
            except Exception as e:
                print(f"[Workflow] 知识图谱检索失败: {e}")
                context["knowledge_context"] = {"error": str(e)}

        if use_vector_db and self.vector_retriever:
            try:
                query = user_query or f"低空空域风险评估 {region}"
                context["vector_context"] = self.vector_retriever.get_relevant_context(query)
            except Exception as e:
                print(f"[Workflow] 向量数据库检索失败: {e}")

        llm_response = None
        if use_llm and self.llm_client.available:
            try:
                prompt = self._build_assessment_prompt(region, context, user_query)
                system_prompt = (
                    "你是低空空域风险评估专家。请基于提供的上下文信息，"
                    "给出专业、详细的风险评估分析和飞行建议。使用中文。"
                )
                llm_response = self.llm_client.generate(prompt, system_prompt, temperature=0.3)
                context["llm_response"] = llm_response
            except Exception as e:
                print(f"[Workflow] LLM 推理失败: {e}")

        result = {
            "region": region,
            "context": context,
            "assessment_type": "enhanced" if enhanced_analysis else "standard",
            "used_graph_rag": use_knowledge_graph,
            "used_vector_db": use_vector_db,
            "used_llm": use_llm and llm_response is not None,
            "llm_response": llm_response,
            "engine": context.get("engine", "memory"),
            "status": "completed"
        }

        return result

    def _build_assessment_prompt(
        self,
        region: str,
        context: Dict[str, Any],
        user_query: str
    ) -> str:
        parts = [f"请对 {region} 进行低空空域风险评估分析。"]

        kg_context = context.get("knowledge_context")
        if kg_context:
            parts.append("\n## 知识图谱上下文")
            parts.append(f"实体数: {kg_context.get('entity_count', 0)}")
            parts.append(f"关系数: {kg_context.get('relation_count', 0)}")
            parts.append(f"风险因素数: {kg_context.get('risk_factor_count', 0)}")
            parts.append(f"知识引擎: {kg_context.get('engine', 'memory')}")

            summary = kg_context.get('summary', '')
            if summary:
                parts.append(f"\n摘要: {summary}")

            risk_factors = kg_context.get('risk_factors', [])
            if risk_factors:
                parts.append("\n风险因素:")
                for rf in risk_factors:
                    parts.append(f"- {rf.get('name', '')}: 权重={rf.get('weight', 0)}, 风险值={rf.get('value', 0)}")

            key_infra = kg_context.get('key_infrastructure', [])
            if key_infra:
                parts.append(f"\n关键基础设施: {', '.join(key_infra)}")

            key_areas = kg_context.get('key_sensitive_areas', [])
            if key_areas:
                parts.append(f"\n敏感区域: {', '.join(key_areas)}")

            key_paths = kg_context.get('key_paths', [])
            if key_paths:
                parts.append("\n关键风险路径:")
                for path in key_paths:
                    parts.append(f"- {path}")

        vector_context = context.get("vector_context")
        if vector_context:
            parts.append(f"\n## 向量检索上下文\n{vector_context}")

        if user_query:
            parts.append(f"\n## 用户查询\n{user_query}")

        parts.append("\n请生成专业的风险评估报告。")
        return "\n".join(parts)

    def execute_with_lora_model(self, region: str, user_query: str = "") -> Dict[str, Any]:
        """
        使用 LoRA 微调模型执行风险评估

        Args:
            region: 区域名称
            user_query: 用户查询

        Returns:
            评估结果
        """
        self.status = WorkflowStatus.RUNNING

        try:
            kg_context = self.graph_rag.get_context_for_report(region)

            prompt = self._build_assessment_prompt(region, {
                "knowledge_context": kg_context,
                "vector_context": None
            }, user_query)

            system_prompt = (
                "你是低空空域风险评估专家。请基于提供的知识图谱上下文，"
                "给出专业、详细的风险评估分析和飞行建议。使用中文。"
            )

            llm_response = self.llm_client.generate(prompt, system_prompt, temperature=0.3)

            self.result = {
                "region": region,
                "knowledge_context": kg_context,
                "llm_response": llm_response,
                "engine": kg_context.get("engine", "memory"),
                "lora_used": self.llm_client.peft_loaded,
                "status": "completed"
            }

            self.status = WorkflowStatus.COMPLETED
            return self.result

        except Exception as e:
            self.error = str(e)
            self.status = WorkflowStatus.FAILED
            raise