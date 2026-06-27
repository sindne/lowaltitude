import sys
import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict, deque
_LOCAL_PACKAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_local_packages"
)
if os.path.isdir(_LOCAL_PACKAGES_DIR) and _LOCAL_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _LOCAL_PACKAGES_DIR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knowledge_graph.in_memory_graph import get_graph_store, InMemoryGraphStore
from knowledge_graph.local_llm_client import get_local_llm, LocalLLMClient
_MICROSOFT_GRAPHRAG_AVAILABLE = None
_GRAPHRAG_INDEX_AVAILABLE = None
_GRAPHRAG_QUERY_AVAILABLE = None
_GRAPHRAG_IMPORT_ERROR = None
def _check_graphrag_available() -> bool:
    global _MICROSOFT_GRAPHRAG_AVAILABLE, _GRAPHRAG_IMPORT_ERROR
    if _MICROSOFT_GRAPHRAG_AVAILABLE is not None:
        return _MICROSOFT_GRAPHRAG_AVAILABLE
    try:
        import graphrag
        _MICROSOFT_GRAPHRAG_AVAILABLE = True
        print("[GraphRAG] Microsoft GraphRAG core library loaded")
    except ImportError as e:
        _MICROSOFT_GRAPHRAG_AVAILABLE = False
        _GRAPHRAG_IMPORT_ERROR = str(e)
        print("[GraphRAG] Microsoft GraphRAG core library not available")
    return _MICROSOFT_GRAPHRAG_AVAILABLE
def _check_graphrag_index_available() -> bool:
    global _GRAPHRAG_INDEX_AVAILABLE
    if _GRAPHRAG_INDEX_AVAILABLE is not None:
        return _GRAPHRAG_INDEX_AVAILABLE
    if not _check_graphrag_available():
        _GRAPHRAG_INDEX_AVAILABLE = False
        return False
    try:
        from graphrag.config.load_config import load_config
        from graphrag.config.models.graph_rag_config import GraphRagConfig
        from graphrag.index.run.run_pipeline import run_pipeline
        from graphrag.callbacks.console_workflow_callbacks import ConsoleWorkflowCallbacks
        _GRAPHRAG_INDEX_AVAILABLE = True
        print("[GraphRAG] Microsoft GraphRAG index pipeline available")
    except ImportError as e:
        _GRAPHRAG_INDEX_AVAILABLE = False
        print(f"[GraphRAG] Microsoft GraphRAG index pipeline not available: {e}")
    return _GRAPHRAG_INDEX_AVAILABLE
def _check_graphrag_query_available() -> bool:
    global _GRAPHRAG_QUERY_AVAILABLE
    if _GRAPHRAG_QUERY_AVAILABLE is not None:
        return _GRAPHRAG_QUERY_AVAILABLE
    if not _check_graphrag_available():
        _GRAPHRAG_QUERY_AVAILABLE = False
        return False
    try:
        from graphrag.query.factory import get_local_search_engine, get_global_search_engine
        from graphrag.query.indexer_adapters import (
            read_indexer_entities,
            read_indexer_relationships,
            read_indexer_reports,
            read_indexer_text_units,
            read_indexer_covariates,
        )
        from graphrag.data_model.entity import Entity as GraphRagEntity
        from graphrag.data_model.relationship import Relationship as GraphRagRelationship
        from graphrag.data_model.community_report import CommunityReport
        from graphrag.data_model.text_unit import TextUnit
        from graphrag.data_model.community import Community
        from graphrag.data_model.covariate import Covariate
        import pandas as pd
        _GRAPHRAG_QUERY_AVAILABLE = True
        print("[GraphRAG] Microsoft GraphRAG query engine available")
    except ImportError as e:
        _GRAPHRAG_QUERY_AVAILABLE = False
        print(f"[GraphRAG] Microsoft GraphRAG query engine not available: {e}")
    return _GRAPHRAG_QUERY_AVAILABLE
class MicrosoftGraphRAGEngine:
    def __init__(self, workspace_dir: str = None):
        self._available = False
        self._index_available = False
        self._query_available = False
        self._indexed = False
        self._workspace_dir = workspace_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "graphrag_workspace"
        )
        self._entities: List[Any] = []
        self._relationships: List[Any] = []
        self._communities: List[Any] = []
        self._community_reports: List[Any] = []
        self._text_units: List[Any] = []
        self._covariates: List[Any] = []
        self._local_search_engine = None
        self._global_search_engine = None
        self._config: Optional[Any] = None
        self._init_workspace()
    @property
    def available(self) -> bool:
        return self._available and self._indexed
    @property
    def query_available(self) -> bool:
        return self._query_available and self._indexed
    def _init_workspace(self):
        os.makedirs(self._workspace_dir, exist_ok=True)
        os.makedirs(os.path.join(self._workspace_dir, "input"), exist_ok=True)
        os.makedirs(os.path.join(self._workspace_dir, "output"), exist_ok=True)
        os.makedirs(os.path.join(self._workspace_dir, "cache"), exist_ok=True)
        os.makedirs(os.path.join(self._workspace_dir, "logs"), exist_ok=True)
        self._ensure_settings_yaml()
    def _ensure_settings_yaml(self):
        settings_path = os.path.join(self._workspace_dir, "settings.yaml")
        if os.path.exists(settings_path):
            return
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(default_settings)
            print(f"[MSGraphRAG] Default settings.yaml created at {settings_path}")
        except Exception as e:
            print(f"[MSGraphRAG] Failed to create settings.yaml: {e}")
    def index_documents(
        self,
        documents: List[str],
        entity_types: Optional[List[str]] = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self._available or not self._index_available:
            print("[MSGraphRAG] Index pipeline not available, skipping indexing")
            return False
        try:
            doc_path = os.path.join(self._workspace_dir, "input", "documents.txt")
            with open(doc_path, 'w', encoding='utf-8') as f:
                for i, doc in enumerate(documents):
                    f.write(f"Document {i+1}:\n{doc}\n\n")
            print(f"[MSGraphRAG] Written {len(documents)} documents to {doc_path}")
            config = load_config(
                root_dir=self._workspace_dir,
                cli_overrides=config_overrides or {},
            )
            self._config = config
            callbacks = ConsoleWorkflowCallbacks()
            print("[MSGraphRAG] Starting indexing pipeline...")
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            async def _run():
                results = []
                async for result in run_pipeline(
                    pipeline=config.pipelines[0] if hasattr(config, 'pipelines') and config.pipelines else None,
                    config=config,
                    callbacks=callbacks,
                ):
                    results.append(result)
                return results
            pipeline_results = asyncio.run(_run())
            print(f"[MSGraphRAG] Pipeline completed with {len(pipeline_results)} workflow results")
            self._indexed = True
            self._load_indexed_data()
            print("[MSGraphRAG] Indexing complete")
            return True
        except Exception as e:
            print(f"[MSGraphRAG] Indexing failed: {e}")
            import traceback
            traceback.print_exc()
            self._indexed = False
            return False
    def _load_indexed_data(self):
        if not self._query_available:
            return
        try:
            output_dir = os.path.join(self._workspace_dir, "output")
            entities_path = os.path.join(output_dir, "create_final_entities.parquet")
            if os.path.exists(entities_path):
                entities_df = pd.read_parquet(entities_path)
                self._entities = read_indexer_entities(entities_df, None, community_level=2)
                print(f"[MSGraphRAG] Loaded {len(self._entities)} entities")
            relationships_path = os.path.join(output_dir, "create_final_relationships.parquet")
            if os.path.exists(relationships_path):
                rels_df = pd.read_parquet(relationships_path)
                self._relationships = read_indexer_relationships(rels_df)
                print(f"[MSGraphRAG] Loaded {len(self._relationships)} relationships")
            communities_path = os.path.join(output_dir, "create_final_communities.parquet")
            if os.path.exists(communities_path):
                communities_df = pd.read_parquet(communities_path)
                self._communities = read_indexer_entities(communities_df, None, community_level=2)
                print(f"[MSGraphRAG] Loaded {len(self._communities)} communities")
            reports_path = os.path.join(output_dir, "create_final_community_reports.parquet")
            if os.path.exists(reports_path):
                reports_df = pd.read_parquet(reports_path)
                self._community_reports = read_indexer_reports(reports_df, None, community_level=2)
                print(f"[MSGraphRAG] Loaded {len(self._community_reports)} community reports")
            text_units_path = os.path.join(output_dir, "create_final_text_units.parquet")
            if os.path.exists(text_units_path):
                text_units_df = pd.read_parquet(text_units_path)
                self._text_units = read_indexer_text_units(text_units_df)
                print(f"[MSGraphRAG] Loaded {len(self._text_units)} text units")
            covariates_path = os.path.join(output_dir, "create_final_covariates.parquet")
            if os.path.exists(covariates_path):
                covariates_df = pd.read_parquet(covariates_path)
                self._covariates = read_indexer_covariates(covariates_df)
                print(f"[MSGraphRAG] Loaded {len(self._covariates)} covariates")
        except Exception as e:
            print(f"[MSGraphRAG] Failed to load indexed data: {e}")
            import traceback
            traceback.print_exc()
    def _ensure_search_engines(self):
        if not self._query_available or not self._indexed:
            return
        try:
            from graphrag_vectors import create_vector_store, VectorStoreConfig, VectorStoreType
            from graphrag.config.embeddings import default_embeddings
            if self._local_search_engine is None and self._community_reports:
                vector_store_config = VectorStoreConfig(
                    type=VectorStoreType.LanceDB,
                    db_uri=os.path.join(self._workspace_dir, "output", "lancedb"),
                    container_name="default",
                    overwrite=True,
                )
                description_embedding_store = create_vector_store(
                    vector_store_config,
                    collection_name="default-entity-description",
                )
                self._local_search_engine = get_local_search_engine(
                    config=self._config,
                    reports=self._community_reports,
                    text_units=self._text_units,
                    entities=self._entities,
                    relationships=self._relationships,
                    covariates={"claims": self._covariates} if self._covariates else {},
                    response_type="Multiple Paragraphs",
                    description_embedding_store=description_embedding_store,
                )
                print("[MSGraphRAG] Local search engine initialized")
            if self._global_search_engine is None and self._community_reports:
                self._global_search_engine = get_global_search_engine(
                    config=self._config,
                    reports=self._community_reports,
                    entities=self._entities,
                    communities=self._communities,
                    response_type="Multiple Paragraphs",
                )
                print("[MSGraphRAG] Global search engine initialized")
        except Exception as e:
            print(f"[MSGraphRAG] Failed to initialize search engines: {e}")
    def local_search(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        if not self.query_available:
            return {
                "entities": [], "relationships": [], "reports": [],
                "response": "", "context_data": {}, "error": "Query engine not available"
            }
        try:
            self._ensure_search_engines()
            if self._local_search_engine is None:
                return {"entities": [], "relationships": [], "response": "", "error": "Search engine not initialized"}
            result = self._local_search_engine.search(query)
            response_text = ""
            if hasattr(result, 'response'):
                response_text = str(result.response)
            elif isinstance(result, str):
                response_text = result
            context_data = {}
            if hasattr(result, 'context_data'):
                context_data = result.context_data
            elif hasattr(result, 'context_text'):
                context_data = {"context_text": result.context_text}
            entities_out = []
            for e in self._entities[:top_k]:
                entities_out.append({
                    "id": e.id if hasattr(e, 'id') else str(e),
                    "title": e.title if hasattr(e, 'title') else "",
                    "type": e.type if hasattr(e, 'type') else "",
                    "description": e.description if hasattr(e, 'description') else "",
                })
            relationships_out = []
            for r in self._relationships[:top_k]:
                relationships_out.append({
                    "source": r.source if hasattr(r, 'source') else "",
                    "target": r.target if hasattr(r, 'target') else "",
                    "description": r.description if hasattr(r, 'description') else "",
                })
            return {
                "response": response_text,
                "context_data": context_data,
                "entities": entities_out,
                "relationships": relationships_out,
            }
        except Exception as e:
            print(f"[MSGraphRAG] Local search failed: {e}")
            import traceback
            traceback.print_exc()
            return {"entities": [], "relationships": [], "response": "", "error": str(e)}
    def global_search(self, query: str) -> Dict[str, Any]:
        if not self.query_available:
            return {"response": "", "context_data": {}, "error": "Query engine not available"}
        try:
            self._ensure_search_engines()
            if self._global_search_engine is None:
                return {"response": "", "error": "Global search engine not initialized"}
            result = self._global_search_engine.search(query)
            response_text = ""
            if hasattr(result, 'response'):
                response_text = str(result.response)
            elif isinstance(result, str):
                response_text = result
            context_data = {}
            if hasattr(result, 'context_data'):
                context_data = result.context_data
            return {
                "response": response_text,
                "context_data": context_data,
            }
        except Exception as e:
            print(f"[MSGraphRAG] Global search failed: {e}")
            return {"response": "", "error": str(e)}
    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        if not self._entities:
            return []
        return [
            {
                "id": e.id if hasattr(e, 'id') else str(e),
                "title": e.title if hasattr(e, 'title') else "",
                "type": e.type if hasattr(e, 'type') else "",
                "description": e.description if hasattr(e, 'description') else "",
            }
            for e in self._entities
            if hasattr(e, 'type') and e.type == entity_type
        ]
    def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        if not self._relationships:
            return []
        return [
            {
                "source": r.source if hasattr(r, 'source') else "",
                "target": r.target if hasattr(r, 'target') else "",
                "description": r.description if hasattr(r, 'description') else "",
            }
            for r in self._relationships
            if (hasattr(r, 'source') and r.source == entity_id)
            or (hasattr(r, 'target') and r.target == entity_id)
        ]
    def load_existing_index(self) -> bool:
        output_dir = os.path.join(self._workspace_dir, "output")
        entities_path = os.path.join(output_dir, "create_final_entities.parquet")
        if not os.path.exists(entities_path):
            print("[MSGraphRAG] No existing index found")
            return False
        try:
            self._load_indexed_data()
            if self._entities:
                self._indexed = True
                settings_path = os.path.join(self._workspace_dir, "settings.yaml")
                if os.path.exists(settings_path):
                    self._config = load_config(root_dir=self._workspace_dir)
                print(f"[MSGraphRAG] Existing index loaded: {len(self._entities)} entities")
                return True
        except Exception as e:
            print(f"[MSGraphRAG] Failed to load existing index: {e}")
        return False
class GraphRAG:
    def __init__(self):
        self._graph_store: Optional[InMemoryGraphStore] = None
        self._llm: Optional[LocalLLMClient] = None
        self._case_builder = None
        self._query_cache: Dict[str, Any] = {}
        self._loaded_cities: set = set()
        self._ms_graphrag: Optional[MicrosoftGraphRAGEngine] = None
        self._ms_graphrag_initialized = False
    def _init_ms_graphrag(self):
        if self._ms_graphrag_initialized:
            return
        self._ms_graphrag_initialized = True
        if not _check_graphrag_available():
            return
        try:
            self._ms_graphrag = MicrosoftGraphRAGEngine()
            self._ms_graphrag.load_existing_index()
            if self._ms_graphrag.available:
                print("[GraphRAG] Microsoft GraphRAG engine ready")
            else:
                print("[GraphRAG] Microsoft GraphRAG engine initialized (awaiting indexing)")
        except Exception as e:
            print(f"[GraphRAG] Microsoft GraphRAG initialization failed: {e}")
            self._ms_graphrag = None
    def set_graph_store(self, store: InMemoryGraphStore):
        self._graph_store = store
    def set_llm(self, llm: LocalLLMClient):
        self._llm = llm
    def set_case_builder(self, builder):
        self._case_builder = builder
    def index_documents_with_ms_graphrag(
        self,
        documents: List[str],
        entity_types: Optional[List[str]] = None
    ) -> bool:
        if self._ms_graphrag is None:
            print("[GraphRAG] Microsoft GraphRAG not available, cannot index")
            return False
        return self._ms_graphrag.index_documents(documents, entity_types)
    @property
    def available(self) -> bool:
        return self._graph_store is not None and self._graph_store.available
    @property
    def ms_graphrag_available(self) -> bool:
        self._init_ms_graphrag()
        return self._ms_graphrag is not None and self._ms_graphrag.available
    @property
    def llm_available(self) -> bool:
        return self._llm is not None and self._llm.available
    def retrieve_for_risk_assessment(
        self,
        city_name: str,
        query: str = ""
    ) -> Dict[str, Any]:
        result = {
            'city_name': city_name,
            'subgraph': {'entities': [], 'relations': []},
            'summary': '',
            'risk_factors': [],
            'infrastructure': [],
            'sensitive_areas': [],
            'key_paths': [],
            'graph_statistics': {},
            'case_insights': '',
            'ms_graphrag_result': None,
            'engine': 'memory',
            'retrieval_timestamp': datetime.now().isoformat()
        }
        if self.ms_graphrag_available:
            search_query = query or f"Low-altitude airspace risk assessment {city_name} risk factors infrastructure sensitive areas"
            try:
                ms_result = self._ms_graphrag.local_search(search_query)
                result['ms_graphrag_result'] = ms_result
                result['engine'] = 'microsoft_graphrag'
                if ms_result.get('entities'):
                    for entity in ms_result.get('entities', []):
                        etype = entity.get('type', '')
                        if etype in ('risk_factor', 'RISK_FACTOR'):
                            result['risk_factors'].append(entity)
                        elif etype in ('infrastructure', 'INFRASTRUCTURE'):
                            result['infrastructure'].append(entity)
                        elif etype in ('sensitive_area', 'SENSITIVE_AREA'):
                            result['sensitive_areas'].append(entity)
                    result['graph_statistics'] = {
                        'total_entities': len(ms_result.get('entities', [])),
                        'total_relations': len(ms_result.get('relationships', [])),
                        'entity_types': {}
                    }
                    result['summary'] = ms_result.get('response', '')[:500] if ms_result.get('response') else ''
                    result['subgraph'] = {
                        'entities': ms_result.get('entities', []),
                        'relations': ms_result.get('relationships', [])
                    }
                    return result
            except Exception as e:
                print(f"[GraphRAG] Microsoft GraphRAG retrieval failed, falling back to memory: {e}")
        if not self.available:
            result['summary'] = "[GraphRAG unavailable]"
            return result
        subgraph = self._graph_store.query_subgraph(city_name, max_depth=3)
        result['subgraph'] = subgraph
        entities = subgraph.get('entities', [])
        relations = subgraph.get('relations', [])
        for entity in entities:
            etype = entity.get('entity_type', '')
            if etype == 'risk_factor':
                result['risk_factors'].append(entity)
            elif etype == 'infrastructure':
                result['infrastructure'].append(entity)
            elif etype == 'sensitive_area':
                result['sensitive_areas'].append(entity)
        type_counts = defaultdict(int)
        for e in entities:
            type_counts[e.get('entity_type', 'unknown')] += 1
        result['graph_statistics'] = {
            'total_entities': len(entities),
            'total_relations': len(relations),
            'entity_types': dict(type_counts)
        }
        result['summary'] = self._generate_summary(
            city_name,
            result['risk_factors'],
            result['infrastructure'],
            result['sensitive_areas'],
            len(relations)
        )
        result['key_paths'] = self._find_risk_paths(entities, relations, city_name)
        result['case_insights'] = self._get_case_insights(city_name)
        return result
    def build_rag_prompt(
        self,
        retrieval_result: Dict[str, Any],
        user_query: str,
        include_full_graph: bool = False
    ) -> str:
        city_name = retrieval_result.get('city_name', '')
        summary = retrieval_result.get('summary', '')
        risk_factors = retrieval_result.get('risk_factors', [])
        infrastructure = retrieval_result.get('infrastructure', [])
        sensitive_areas = retrieval_result.get('sensitive_areas', [])
        key_paths = retrieval_result.get('key_paths', [])
        case_insights = retrieval_result.get('case_insights', '')
        stats = retrieval_result.get('graph_statistics', {})
        engine = retrieval_result.get('engine', 'memory')
        ms_result = retrieval_result.get('ms_graphrag_result')
        parts = []
        parts.append("=" * 60)
        parts.append(f"[GraphRAG Knowledge Graph Context] Engine: {engine}")
        parts.append("=" * 60)
        if ms_result and ms_result.get('response'):
            parts.append(f"\n## Microsoft GraphRAG Results")
            parts.append(ms_result['response'][:1000])
        if summary:
            parts.append(f"\n## Knowledge Graph Summary\n{summary}")
        if stats:
            parts.append(f"\n## Graph Statistics")
            parts.append(f"- Total Entities: {stats.get('total_entities', 0)}")
            parts.append(f"- Total Relations: {stats.get('total_relations', 0)}")
        if risk_factors:
            parts.append(f"\n## Risk Factors ({len(risk_factors)})")
            for rf in risk_factors:
                name = rf.get('name', rf.get('title', ''))
                props = rf.get('properties', {})
                weight = props.get('weight', 0)
                value = props.get('value', 0)
                parts.append(f"- {name}: weight={weight}, value={value}")
        if infrastructure:
            parts.append(f"\n## Infrastructure ({len(infrastructure)})")
            for infra in infrastructure[:8]:
                parts.append(f"- {infra.get('name', infra.get('title', ''))}")
        if sensitive_areas:
            parts.append(f"\n## Sensitive Areas ({len(sensitive_areas)})")
            for sa in sensitive_areas[:8]:
                parts.append(f"- {sa.get('name', sa.get('title', ''))}")
        if key_paths:
            parts.append(f"\n## Key Risk Paths")
            for i, path in enumerate(key_paths[:3]):
                path_str = " -> ".join(path.get('nodes', []))
                parts.append(f"{i + 1}. {path_str}")
        if case_insights:
            parts.append(f"\n## Historical Case Insights\n{case_insights}")
        if include_full_graph:
            parts.append(f"\n## Full Graph Data")
            parts.append(json.dumps(retrieval_result.get('subgraph', {}), ensure_ascii=False, indent=2)[:2000])
        parts.append("\n" + "=" * 60)
        parts.append(f"[User Query] {user_query}")
        parts.append("=" * 60)
        parts.append("\nBased on the above knowledge graph context, provide a professional analysis.")
        return "\n".join(parts)
    def retrieve_and_prompt(
        self,
        city_name: str,
        user_query: str
    ) -> Tuple[str, Dict[str, Any]]:
        retrieval = self.retrieve_for_risk_assessment(city_name, user_query)
        prompt = self.build_rag_prompt(retrieval, user_query)
        return prompt, retrieval
    def generate_with_graph_rag(
        self,
        city_name: str,
        user_query: str,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        prompt, retrieval = self.retrieve_and_prompt(city_name, user_query)
        result = {
            'success': True,
            'city_name': city_name,
            'query': user_query,
            'retrieval': retrieval,
            'prompt': prompt,
            'response': '',
            'used_llm': False
        }
        if use_llm and self.llm_available:
            try:
                system_prompt = (
                    "You are a low-altitude airspace risk assessment expert. "
                    "Based on the knowledge graph context, provide a professional, "
                    "detailed risk assessment analysis and flight recommendations. Respond in Chinese."
                )
                response = self._llm.generate(prompt, system_prompt, temperature=0.3)
                if response:
                    result['response'] = response
                    result['used_llm'] = True
            except Exception as e:
                print(f"[GraphRAG] LLM generation failed: {e}")
                result['response'] = f"[LLM generation failed: {e}]"
        return result
    def get_context_for_report(self, city_name: str) -> Dict[str, Any]:
        retrieval = self.retrieve_for_risk_assessment(city_name)
        risk_factors = retrieval.get('risk_factors', [])
        infrastructure = retrieval.get('infrastructure', [])
        sensitive_areas = retrieval.get('sensitive_areas', [])
        stats = retrieval.get('graph_statistics', {})
        return {
            'city_name': city_name,
            'entity_count': stats.get('total_entities', 0),
            'relation_count': stats.get('total_relations', 0),
            'risk_factor_count': len(risk_factors),
            'infrastructure_count': len(infrastructure),
            'sensitive_area_count': len(sensitive_areas),
            'risk_factors': [
                {
                    'name': rf.get('name', rf.get('title', '')),
                    'weight': rf.get('properties', {}).get('weight', 0),
                    'value': rf.get('properties', {}).get('value', 0)
                }
                for rf in risk_factors
            ],
            'key_infrastructure': [
                infra.get('name', infra.get('title', ''))
                for infra in infrastructure[:5]
            ],
            'key_sensitive_areas': [
                sa.get('name', sa.get('title', ''))
                for sa in sensitive_areas[:5]
            ],
            'summary': retrieval.get('summary', ''),
            'engine': retrieval.get('engine', 'memory'),
            'key_paths': [
                ' -> '.join(p.get('nodes', []))
                for p in retrieval.get('key_paths', [])[:3]
            ]
        }
    def search_entities(
        self,
        query_text: str,
        city_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        if self.ms_graphrag_available:
            try:
                ms_result = self._ms_graphrag.local_search(query_text, top_k=limit)
                if ms_result.get('entities'):
                    return ms_result['entities'][:limit]
            except Exception:
                pass
        if not self.available:
            return []
        return self._graph_store.semantic_search(query_text, city_name, limit)
    def get_entity_detail(self, entity_id: str) -> Dict[str, Any]:
        if not self.available:
            return {'entity': None, 'relations': [], 'neighbors': []}
        return self._graph_store.get_connected_entities(entity_id)
    def compare_cities(self, city_names: List[str]) -> Dict[str, Any]:
        comparison = {}
        for city in city_names:
            retrieval = self.retrieve_for_risk_assessment(city)
            comparison[city] = {
                'entity_count': retrieval['graph_statistics'].get('total_entities', 0),
                'relation_count': retrieval['graph_statistics'].get('total_relations', 0),
                'risk_factor_count': len(retrieval['risk_factors']),
                'infrastructure_count': len(retrieval['infrastructure']),
                'sensitive_area_count': len(retrieval['sensitive_areas']),
                'engine': retrieval.get('engine', 'memory'),
            }
        return comparison
    def build_and_index_cases(self) -> int:
        if not self._case_builder:
            from knowledge_graph.case_kg_builder import get_case_kg_builder
            self._case_builder = get_case_kg_builder()
        self._case_builder.load_all_cases()
        unified_kg = self._case_builder.build_unified_kg()
        unified_dict = unified_kg.to_dict()
        if self._graph_store:
            self._graph_store.save_knowledge_graph(
                city_name='__unified__',
                entities=unified_dict.get('entities', []),
                relations=unified_dict.get('relations', []),
                metadata={'type': 'unified_case_kg'}
            )
        for case in self._case_builder.get_cases():
            city = case.get('city', '')
            if city and city != '__unified__':
                kg_data = case.get('kg_data', {})
                if kg_data:
                    self._graph_store.save_knowledge_graph(
                        city_name=city,
                        entities=kg_data.get('entities', []),
                        relations=kg_data.get('relations', []),
                        metadata={'source': case.get('source', 'unknown')}
                    )
                self._loaded_cities.add(city)
        if self._ms_graphrag and _check_graphrag_available():
            try:
                documents = []
                for case in self._case_builder.get_cases():
                    city = case.get('city', '')
                    kg_data = case.get('kg_data', {})
                    entities = kg_data.get('entities', [])
                    relations = kg_data.get('relations', [])
                    doc = f"City: {city}\n"
                    doc += f"Entities: {len(entities)}, Relations: {len(relations)}\n"
                    for e in entities:
                        doc += f"Entity: {e.get('name', '')} (Type: {e.get('entity_type', '')})\n"
                    for r in relations:
                        doc += f"Relation: {r.get('source_id', '')} -> {r.get('relation_type', '')} -> {r.get('target_id', '')}\n"
                    documents.append(doc)
                if documents:
                    self._ms_graphrag.index_documents(documents)
                    print("[GraphRAG] Case knowledge graph indexed with Microsoft GraphRAG")
            except Exception as e:
                print(f"[GraphRAG] Microsoft GraphRAG case indexing failed: {e}")
        return len(self._case_builder.get_cases())
    def _generate_summary(
        self,
        city_name: str,
        risk_factors: List[Dict],
        infrastructure: List[Dict],
        sensitive_areas: List[Dict],
        relation_count: int
    ) -> str:
        parts = [f"{city_name} knowledge graph contains:"]
        if risk_factors:
            names = [rf.get('name', rf.get('title', '')) for rf in risk_factors]
            parts.append(f"- {len(risk_factors)} risk factors: {', '.join(names)}")
        if infrastructure:
            names = [infra.get('name', infra.get('title', '')) for infra in infrastructure[:5]]
            more = f" and {len(infrastructure)} more" if len(infrastructure) > 5 else ""
            parts.append(f"- {len(infrastructure)} infrastructure items: {', '.join(names)}{more}")
        if sensitive_areas:
            names = [sa.get('name', sa.get('title', '')) for sa in sensitive_areas[:5]]
            more = f" and {len(sensitive_areas)} more" if len(sensitive_areas) > 5 else ""
            parts.append(f"- {len(sensitive_areas)} sensitive areas: {', '.join(names)}{more}")
        parts.append(f"- {relation_count} entity relationships")
        return "\n".join(parts)
    def _find_risk_paths(
        self,
        entities: List[Dict],
        relations: List[Dict],
        city_name: str
    ) -> List[Dict[str, Any]]:
        entity_map = {e['id']: e for e in entities}
        adj = defaultdict(list)
        for rel in relations:
            src = rel.get('source_id', '')
            tgt = rel.get('target_id', '')
            rtype = rel.get('relation_type', '')
            if src and tgt:
                adj[src].append((tgt, rtype))
        start_entities = [
            e for e in entities
            if e.get('entity_type') in ('sensitive_area', 'infrastructure')
        ]
        end_entities = [
            e for e in entities
            if e.get('entity_type') == 'risk_factor'
        ]
        paths = []
        found = 0
        for start in start_entities[:5]:
            for end in end_entities[:3]:
                if found >= 5:
                    break
                path = self._bfs_path(adj, entity_map, start['id'], end['id'])
                if path:
                    paths.append({
                        'nodes': path['nodes'],
                        'relation_types': path['relation_types'],
                        'description': (
                            f"{path['nodes'][0]} via "
                            f"{path['relation_types'][0] if path['relation_types'] else 'association'} "
                            f"affects {path['nodes'][-1]}"
                        )
                    })
                    found += 1
        return paths
    def _bfs_path(
        self,
        adj,
        entity_map: Dict[str, Dict],
        start_id: str,
        end_id: str,
        max_depth: int = 3
    ) -> Optional[Dict[str, Any]]:
        queue = deque([(start_id, [start_id], [])])
        visited = {start_id}
        while queue:
            current, path, rel_types = queue.popleft()
            if len(path) > max_depth + 1:
                continue
            if current == end_id:
                node_names = [
                    entity_map.get(nid, {}).get('name', nid)
                    for nid in path
                ]
                return {'nodes': node_names, 'relation_types': rel_types}
            for neighbor, rtype in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor], rel_types + [rtype]))
        return None
    def _get_case_insights(self, city_name: str) -> str:
        if not self._case_builder:
            return ""
        city_cases = self._case_builder.get_cases_by_city(city_name)
        if not city_cases:
            return ""
        risk_counts = defaultdict(int)
        for c in city_cases:
            risk_counts[c.get('risk_level', 'Unknown')] += 1
        parts = [
            f"Historical assessments: {len(city_cases)} records",
            f"Risk distribution: {dict(risk_counts)}",
            f"Data sources: {', '.join(set(c.get('source', '') for c in city_cases))}"
        ]
        return '\n'.join(parts)
    def clear_cache(self):
        self._query_cache.clear()
_graph_rag: Optional[GraphRAG] = None
def get_graph_rag() -> GraphRAG:
    global _graph_rag
    if _graph_rag is None:
        _graph_rag = GraphRAG()
    return _graph_rag
def set_graph_rag(graph_rag: GraphRAG):
    global _graph_rag
    _graph_rag = graph_rag