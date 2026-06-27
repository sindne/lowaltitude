"""
知识图谱模块 - 低空空域专业知识图谱
基于内存图存储 + GraphRAG 检索增强生成
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.schema import (
    Entity,
    Relation,
    KnowledgeGraph,
    AirspaceRegion,
    RiskFactor,
    Infrastructure,
    SensitiveArea,
    WeatherData
)
from knowledge_graph.builder import KnowledgeGraphBuilder
from knowledge_graph.extractor import StructuredInfoExtractor
from knowledge_graph.storage import KnowledgeGraphStorage
from knowledge_graph.in_memory_graph import InMemoryGraphStore, get_graph_store

__all__ = [
    'Entity',
    'Relation',
    'KnowledgeGraph',
    'AirspaceRegion',
    'RiskFactor',
    'Infrastructure',
    'SensitiveArea',
    'WeatherData',
    'KnowledgeGraphBuilder',
    'StructuredInfoExtractor',
    'KnowledgeGraphStorage',
    'GraphRAG',
    'get_graph_rag',
    'MicrosoftGraphRAGEngine',
    'InMemoryGraphStore',
    'get_graph_store',
    'CaseKnowledgeGraphBuilder',
    'get_case_kg_builder',
    'LocalLLMClient',
    'get_local_llm'
]


def __getattr__(name):
    if name == 'GraphRAG':
        from knowledge_graph.graph_rag import GraphRAG as _GraphRAG
        return _GraphRAG
    if name == 'get_graph_rag':
        from knowledge_graph.graph_rag import get_graph_rag as _get_graph_rag
        return _get_graph_rag
    if name == 'MicrosoftGraphRAGEngine':
        from knowledge_graph.graph_rag import MicrosoftGraphRAGEngine as _MicrosoftGraphRAGEngine
        return _MicrosoftGraphRAGEngine
    if name == 'LocalLLMClient':
        from knowledge_graph.local_llm_client import LocalLLMClient as _LocalLLMClient
        return _LocalLLMClient
    if name == 'get_local_llm':
        from knowledge_graph.local_llm_client import get_local_llm as _get_local_llm
        return _get_local_llm
    if name == 'CaseKnowledgeGraphBuilder':
        from knowledge_graph.case_kg_builder import CaseKnowledgeGraphBuilder as _CaseKnowledgeGraphBuilder
        return _CaseKnowledgeGraphBuilder
    if name == 'get_case_kg_builder':
        from knowledge_graph.case_kg_builder import get_case_kg_builder as _get_case_kg_builder
        return _get_case_kg_builder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
