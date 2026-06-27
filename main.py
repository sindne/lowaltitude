import warnings
warnings.filterwarnings("ignore")

import http.server
import socketserver
import json
import urllib.request
import urllib.parse
import math
import threading
import time
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 设置国内镜像源
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HOME"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hf_cache")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hf_cache", "transformers")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import Config, setup_logger
from knowledge_graph import KnowledgeGraphBuilder, KnowledgeGraphStorage, StructuredInfoExtractor
from vector_db import ChromaDBClient, VectorRetriever, IndexManager
from workflows import RiskAssessmentWorkflow, MultiModeController, WorkflowMode, DynamicRouter
from mcp_tools import (
    MonitoringTool, GISTool, AirspaceManagementTool, 
    FlightPlanningTool, DatabaseTool, AccessControlTool
)

# 可选导入：AnalyticsTool
AnalyticsTool = None
try:
    from mcp_tools import AnalyticsTool
except Exception:
    pass
from mcp_tools.enhanced_gis_tools import get_enhanced_gis_tool
from mcp_tools.multi_map_api import get_multi_map_api
from mcp_tools.gis_spatial_operators import get_gis_spatial_operators
from mcp_tools.environmental_factors import get_environmental_factors_processor
from training import LoRATrainer, TrainingDataGenerator, RealDatasetBuilder
from knowledge_graph.dynamic_builder import get_dynamic_builder
from knowledge_graph.knowledge_base import get_knowledge_base

# 可选导入：知识图谱可视化器
_kg_visualizer = None
try:
    from knowledge_graph.visualizer import get_kg_visualizer
    _kg_visualizer_available = True
except Exception as e:
    print(f"[WARNING] 知识图谱可视化器不可用: {e}")
    _kg_visualizer_available = False
    get_kg_visualizer = None

from mcp_tools.data_provider import get_data_provider

# 可选导入：PostGIS数据库
get_postgis_database = None
try:
    from mcp_tools.postgis_database import get_postgis_database
except Exception as e:
    print(f"[WARNING] PostGIS数据库不可用: {e}")

from mcp_tools.enhanced_data_fetcher import get_enhanced_data_fetcher
from mcp_tools.spatial_risk_integration import get_spatial_risk_integration
from mcp_tools.sora_risk_assessment import (
    SORARiskAssessor, DroneSpecs, GroundRiskData, AirRiskData,
    NaturalEnvironmentData, TopologyData, get_sora_assessor
)
from mcp_tools.llm_risk_assessor import LLMRiskAssessor, get_llm_risk_assessor
from evaluation.bleu_evaluator import BLEUEvaluator, evaluate_bleu_from_cases

CHINA_CITY_DATA = {
    "北京": {"population_density": 1330, "building_density": 0.65, "num_airports": 2, "avg_wind_speed_ms": 3.5, "geo_topology_score": 0.7, "has_typhoon": False, "has_sensitive_facilities": True},
    "上海": {"population_density": 3900, "building_density": 0.75, "num_airports": 2, "avg_wind_speed_ms": 4.2, "geo_topology_score": 0.6, "has_typhoon": True, "has_sensitive_facilities": True},
    "广州": {"population_density": 2500, "building_density": 0.70, "num_airports": 1, "avg_wind_speed_ms": 3.8, "geo_topology_score": 0.55, "has_typhoon": True, "has_sensitive_facilities": True},
    "深圳": {"population_density": 6500, "building_density": 0.80, "num_airports": 1, "avg_wind_speed_ms": 3.5, "geo_topology_score": 0.5, "has_typhoon": True, "has_sensitive_facilities": True},
    "武汉": {"population_density": 1200, "building_density": 0.60, "num_airports": 1, "avg_wind_speed_ms": 3.0, "geo_topology_score": 0.5, "has_typhoon": False, "has_sensitive_facilities": True},
    "成都": {"population_density": 1200, "building_density": 0.55, "num_airports": 1, "avg_wind_speed_ms": 2.5, "geo_topology_score": 0.6, "has_typhoon": False, "has_sensitive_facilities": True},
    "杭州": {"population_density": 1800, "building_density": 0.60, "num_airports": 1, "avg_wind_speed_ms": 3.5, "geo_topology_score": 0.55, "has_typhoon": True, "has_sensitive_facilities": True},
    "南京": {"population_density": 1400, "building_density": 0.58, "num_airports": 1, "avg_wind_speed_ms": 3.2, "geo_topology_score": 0.55, "has_typhoon": False, "has_sensitive_facilities": True},
    "天津": {"population_density": 1300, "building_density": 0.55, "num_airports": 1, "avg_wind_speed_ms": 4.0, "geo_topology_score": 0.6, "has_typhoon": False, "has_sensitive_facilities": True},
    "重庆": {"population_density": 1200, "building_density": 0.55, "num_airports": 1, "avg_wind_speed_ms": 2.0, "geo_topology_score": 0.7, "has_typhoon": False, "has_sensitive_facilities": True},
    "西安": {"population_density": 1000, "building_density": 0.50, "num_airports": 1, "avg_wind_speed_ms": 2.8, "geo_topology_score": 0.6, "has_typhoon": False, "has_sensitive_facilities": True},
    "长沙": {"population_density": 1100, "building_density": 0.55, "num_airports": 1, "avg_wind_speed_ms": 3.0, "geo_topology_score": 0.55, "has_typhoon": False, "has_sensitive_facilities": True},
    "郑州": {"population_density": 1400, "building_density": 0.55, "num_airports": 1, "avg_wind_speed_ms": 3.2, "geo_topology_score": 0.5, "has_typhoon": False, "has_sensitive_facilities": True},
    "济南": {"population_density": 1100, "building_density": 0.52, "num_airports": 1, "avg_wind_speed_ms": 3.5, "geo_topology_score": 0.55, "has_typhoon": False, "has_sensitive_facilities": True},
    "青岛": {"population_density": 900, "building_density": 0.48, "num_airports": 1, "avg_wind_speed_ms": 5.0, "geo_topology_score": 0.5, "has_typhoon": True, "has_sensitive_facilities": True},
    "哈尔滨": {"population_density": 200, "building_density": 0.35, "num_airports": 1, "avg_wind_speed_ms": 4.5, "geo_topology_score": 0.45, "has_typhoon": False, "has_sensitive_facilities": True},
    "石家庄": {"population_density": 800, "building_density": 0.45, "num_airports": 1, "avg_wind_speed_ms": 3.0, "geo_topology_score": 0.5, "has_typhoon": False, "has_sensitive_facilities": True},
    "黄石": {"population_density": 500, "building_density": 0.40, "num_airports": 0, "avg_wind_speed_ms": 2.8, "geo_topology_score": 0.55, "has_typhoon": False, "has_sensitive_facilities": False},
    "黑龙江": {"population_density": 100, "building_density": 0.25, "num_airports": 1, "avg_wind_speed_ms": 4.0, "geo_topology_score": 0.4, "has_typhoon": False, "has_sensitive_facilities": True},
}

from knowledge_graph.in_memory_graph import InMemoryGraphStore, get_graph_store
from knowledge_graph.graph_rag import GraphRAG, get_graph_rag
from knowledge_graph.case_kg_builder import CaseKnowledgeGraphBuilder, get_case_kg_builder
from knowledge_graph.local_llm_client import LocalLLMClient, get_local_llm

_new_system_initialized = False
_knowledge_graph = None
_vector_db = None
_workflow_controller = None
_mcp_tools = None
_lora_trainer = None
_training_data_generator = None
_real_data_generator = None
_local_inference = None
_structured_info_extractor = None
_vector_retriever = None
_last_assessed_region = '武汉'
_knowledge_base = None
_kg_visualizer = None
_kg_visualizer_available = False
_data_provider = None
_postgis_db = None
_enhanced_data_fetcher = None
_spatial_risk_integration = None
_graph_store = None
_graph_rag = None
_case_kg_builder = None
_local_llm = None

PORT = 5006
AMAP_KEY = '03ee0a418d0fa2a2e5eff463bdec23f6'
BAIDU_MAP_KEY = os.environ.get('BAIDU_MAP_KEY', '')
TENCENT_MAP_KEY = os.environ.get('TENCENT_MAP_KEY', '')
TIANDITU_KEY = os.environ.get('TIANDITU_KEY', '1f3739d13fde53645da61c162c430ce5')
DEEPSEEK_KEY = 'sk-09d148ce6cf34ae68cf87c7a6cb45184'

os.environ.setdefault('AMAP_KEY', AMAP_KEY)
os.environ.setdefault('TIANDITU_KEY', TIANDITU_KEY)

amap_cache = {}
deepseek_cache = {}
cache_lock = threading.Lock()


class LocalInferenceStub:
    """本地推理存根 - 替代已删除的local_model_inference_complete"""
    
    def __init__(self):
        self.model_name = "base_model"
    
    def generate_city_specific_factors(self, region):
        from mcp_tools.ahp_weight_calculator import get_ahp_calculator
        from mcp_tools.llm_weight_adjuster import get_llm_weight_adjuster
        
        ahp_calc = get_ahp_calculator()
        base_weights = ahp_calc.get_default_weights()
        llm_adjuster = get_llm_weight_adjuster(local_llm_client=_local_llm if '_local_llm' in dir() else None)
        
        city_data = CHINA_CITY_DATA.get(region, {})
        adjust_data = {}
        
        if city_data:
            adjust_data = {
                'population_density': city_data.get('population_density', 2000),
                'building_density': city_data.get('building_density', 0.5),
                'num_airports': city_data.get('num_airports', 1),
                'avg_wind_speed': city_data.get('avg_wind_speed_ms', 5.0),
                'geo_topology_score': city_data.get('geo_topology_score', 0.5),
                'has_typhoon': city_data.get('has_typhoon', False),
                'has_sensitive_facilities': city_data.get('has_sensitive_facilities', False),
                'area_km2': city_data.get('area_km2', 5000),
                'annual_flights': city_data.get('annual_flights', 50000)
            }
        
        adjusted_weights = llm_adjuster.adjust_weights_by_llm(base_weights, adjust_data)
        weight_report = llm_adjuster.generate_weight_report(base_weights, adjusted_weights, adjust_data)
        
        pop = city_data.get('population_density', 1000) if city_data else 1000
        bld = city_data.get('building_density', 0.5) if city_data else 0.5
        wind = city_data.get('avg_wind_speed_ms', 5.0) if city_data else 5.0
        
        factors = [
            {"name": "人口密度", "weight": round(adjusted_weights["人口密度"] * 100, 1), "value": min(1.0, pop / 10000)},
            {"name": "空中交通", "weight": round(adjusted_weights["空中交通"] * 100, 1), "value": min(1.0, (city_data.get('num_airports', 1) if city_data else 1) / 5)},
            {"name": "建筑物密度", "weight": round(adjusted_weights["建筑物密度"] * 100, 1), "value": bld},
            {"name": "天气条件", "weight": round(adjusted_weights["天气条件"] * 100, 1), "value": min(1.0, wind / 20)},
            {"name": "地理拓扑", "weight": round(adjusted_weights["地理拓扑"] * 100, 1), "value": city_data.get('geo_topology_score', 0.5) if city_data else 0.5},
        ]
        
        return {
            "factors": factors,
            "city_analysis": f"{region}基于AHP+本地LLM权重的城市特征分析",
            "used_tools": ["ahp_weight_calculator", "llm_weight_adjuster"],
            "model_used": self.model_name,
            "weight_report": weight_report,
            "adjusted_weights": adjusted_weights,
            "base_weights": base_weights
        }
    
    def extract_location(self, user_input):
        for city in CHINA_CITY_DATA:
            if city in user_input:
                return {
                    "primary_location": city,
                    "confidence": 0.9,
                    "all_locations": [city]
                }
        keywords = ["武汉", "北京", "上海", "广州", "深圳", "成都", "杭州", "南京", "天津", "重庆"]
        for kw in keywords:
            if kw in user_input:
                return {
                    "primary_location": kw,
                    "confidence": 0.8,
                    "all_locations": [kw]
                }
        return {
            "primary_location": "武汉",
            "confidence": 0.5,
            "all_locations": []
        }
    
    def get_latest_model(self):
        return self.model_name
    
    @property
    def available(self):
        return True


_local_inference_stub = LocalInferenceStub()


def get_complete_inference():
    return _local_inference_stub


def init_new_system():
    """初始化新系统模块"""
    global _new_system_initialized, _knowledge_graph, _vector_db, _workflow_controller
    global _mcp_tools, _lora_trainer, _training_data_generator
    global _structured_info_extractor, _vector_retriever
    global _knowledge_base, _kg_visualizer, _data_provider, _postgis_db
    global _spatial_risk_integration, _graph_store, _graph_rag, _case_kg_builder, _local_llm
    
    if _new_system_initialized:
        return True
    
    try:
        print("=" * 80)
        print("正在初始化新系统模块...")
        
        print("初始化知识图谱...")
        kg_builder = KnowledgeGraphBuilder()
        kg_storage = KnowledgeGraphStorage()
        
        existing_kg = kg_storage.load()
        if existing_kg:
            _knowledge_graph = existing_kg
            print("  [OK] 已加载现有知识图谱")
        else:
            build_default_knowledge_graph(kg_builder)
            _knowledge_graph = kg_builder.build()
            kg_storage.save(_knowledge_graph)
            print("  [OK] 已创建并保存新知识图谱")
        
        _structured_info_extractor = StructuredInfoExtractor(_knowledge_graph)
        
        print("初始化向量数据库...")
        chroma_client = ChromaDBClient(
            persist_directory=Config.CHROMA_PERSIST_DIR,
            collection_name=Config.CHROMA_COLLECTION_NAME
        )
        _vector_db = {
            'client': chroma_client,
            'retriever': VectorRetriever(chroma_client),
            'index_manager': IndexManager(chroma_client)
        }
        _vector_retriever = _vector_db['retriever']
        
        if chroma_client.count() == 0:
            initialize_vector_database(_vector_db['index_manager'])
        
        print(f"  [OK] 向量数据库就绪，文档数: {chroma_client.count()}")
        
        print("初始化工作流系统...")
        risk_workflow = RiskAssessmentWorkflow(
            vector_retriever=_vector_retriever
        )
        
        _workflow_controller = MultiModeController()
        _workflow_controller.register_workflow(WorkflowMode.STANDARD, risk_workflow)
        _workflow_controller.register_workflow(WorkflowMode.FAST, risk_workflow)
        _workflow_controller.register_workflow(WorkflowMode.PRECISE, risk_workflow)
        _workflow_controller.register_workflow(WorkflowMode.CUSTOM, risk_workflow)
        print("  [OK] 工作流系统就绪")
        
        print("初始化MCP工具集...")
        _mcp_tools = {
            'monitoring': MonitoringTool(),
            'gis': GISTool(),
            'airspace': AirspaceManagementTool(),
            'flight_planning': FlightPlanningTool(),
            'database': DatabaseTool(),
            'access_control': AccessControlTool()
        }
        
        # 只有在AnalyticsTool成功导入时才添加
        if AnalyticsTool is not None:
            _mcp_tools['analytics'] = AnalyticsTool()
        print("  [OK] MCP工具集就绪")
        
        print("初始化LoRA微调系统...")
        try:
            from training.lora_trainer import LoRATrainer
            _lora_trainer = LoRATrainer("./local_models")
            print("  [OK] LoRATrainer 就绪")
        except Exception as e:
            print(f"  [WARNING] LoRATrainer 不可用: {e}")
            _lora_trainer = LoRATrainer()
            print("  [OK] LoRATrainer 基本实例已创建")
        
        from training import TrainingDataGenerator
        _training_data_generator = TrainingDataGenerator()
        print("  [OK] 训练数据生成器就绪")
        
        print("初始化训练数据生成器...")
        from training.simple_data_generator import SimpleTrainingDataGenerator
        _real_data_generator = SimpleTrainingDataGenerator()
        print("  [OK] 训练数据生成器就绪")
        
        print("初始化本地模型推理器...")
        _local_inference = _local_inference_stub
        print("  [OK] 本地模型推理器就绪")
        
        print("初始化知识图谱知识库...")
        _knowledge_base = get_knowledge_base()
        print("  [OK] 知识图谱知识库就绪")
        
        # 注释掉后端知识图谱可视化器初始化，使用前端vis.js可视化
        # print("初始化知识图谱可视化器...")
        # global _kg_visualizer, _kg_visualizer_available
        # if _kg_visualizer_available and get_kg_visualizer is not None:
        #     try:
        #         _kg_visualizer = get_kg_visualizer()
        #         print("  [OK] 知识图谱可视化器就绪")
        #     except Exception as e:
        #         print(f"  [WARNING] 知识图谱可视化器初始化失败: {e}")
        #         _kg_visualizer = None
        # else:
        #     print("  [WARNING] 知识图谱可视化器不可用")
        #     _kg_visualizer = None
        
        print("初始化数据...")
        _data_provider = get_data_provider(AMAP_KEY)
        print("  [OK] 数据就绪")
        
        print("初始化数据获取...")
        global _enhanced_data_fetcher
        _enhanced_data_fetcher = get_enhanced_data_fetcher(AMAP_KEY)
        print("  [OK] 数据获取")
        
        print("初始化PostGIS数据库...")
        try:
            _postgis_db = get_postgis_database(
                host='localhost',
                port=5432,
                database='postgres',
                user='postgres',
                password='035548'
            )
            print("  [OK] PostGIS数据库就绪")
            
            # 导入SHP数据到PostGIS
            print("  正在导入SHP边界数据到PostGIS...")
            try:
                from mcp_tools.custom_shp_reader import get_custom_shp_reader
                shp_reader = get_custom_shp_reader()
                if shp_reader.is_available():
                    print(f"    加载到 {len(shp_reader.data_cache)} 个城市边界数据")
                    imported_count = 0
                    for city_name, city_data in shp_reader.data_cache.items():
                        city_id = _postgis_db.add_city(
                            name=city_name,
                            province=city_data.get('province'),
                            center_lng=city_data.get('center', (0, 0))[0],
                            center_lat=city_data.get('center', (0, 0))[1],
                            city_code=city_data.get('city_code'),
                            area=city_data.get('area'),
                            boundary_coords=city_data.get('coordinates')
                        )
                        if city_id:
                            imported_count += 1
                    print(f"    [OK] 成功导入 {imported_count} 个城市边界到PostGIS")
                else:
                    print("    [WARNING] SHP数据不可用")
            except Exception as shp_error:
                print(f"    [WARNING] SHP数据导入失败: {shp_error}")
                import traceback
                traceback.print_exc()
        except Exception as db_error:
            print(f"  [WARNING] PostGIS数据库连接失败: {db_error}")
            print("  将使用本地数据存储")
        
        # 将PostGIS数据库传递给增强版数据获取器
        if _postgis_db and _enhanced_data_fetcher:
            _enhanced_data_fetcher.set_postgis_db(_postgis_db)
            print("  [OK] 增强版数据获取器已关联PostGIS数据库")
        
        # 将PostGIS数据库和增强版数据获取器传递给数据提供者
        if _data_provider:
            if _postgis_db:
                _data_provider.set_postgis_db(_postgis_db)
                print("  [OK] 数据提供者已关联PostGIS数据库")
            if _enhanced_data_fetcher:
                _data_provider.set_enhanced_data_fetcher(_enhanced_data_fetcher)
                print("  [OK] 数据提供者已关联增强版数据获取器")
        
        # 初始化内存图存储引擎
        print("初始化内存图存储引擎...")
        try:
            _graph_store = get_graph_store()
            print("  [OK] 内存图存储引擎就绪")
        except Exception as e:
            print(f"  [WARNING] 内存图存储初始化失败: {e}")
            _graph_store = None
        
        # 初始化本地大模型客户端
        print("初始化本地大模型客户端...")
        try:
            _local_llm = get_local_llm(
                base_url="http://localhost:8000/v1",
                model_name="llama3-lora"
            )
            if _local_llm.available:
                print("  [OK] 本地 LLaMA 模型已就绪")
            else:
                print("  [WARNING] 本地模型不可用，将使用模板化报告回退")
        except Exception as e:
            print(f"  [WARNING] 本地 LLM 初始化失败: {e}")
            _local_llm = LocalLLMClient()
        
        # 初始化 GraphRAG 检索引擎
        print("初始化 GraphRAG 检索引擎...")
        try:
            _graph_rag = get_graph_rag()
            if _graph_store:
                _graph_rag.set_graph_store(_graph_store)
            if _local_llm:
                _graph_rag.set_llm(_local_llm)
            print("  [OK] GraphRAG 检索引擎就绪")
        except Exception as e:
            print(f"  [WARNING] GraphRAG 初始化失败: {e}")
            _graph_rag = None
        
        # 初始化案例集知识图谱构建器
        print("初始化案例集知识图谱构建器...")
        try:
            _case_kg_builder = get_case_kg_builder()
            if _postgis_db:
                _case_kg_builder.set_postgis_db(_postgis_db)
            from knowledge_graph.dynamic_builder import get_dynamic_builder
            _case_kg_builder.set_dynamic_builder(get_dynamic_builder())
            if _graph_rag:
                _graph_rag.set_case_builder(_case_kg_builder)
            print("  [OK] 案例集知识图谱构建器就绪")
        except Exception as e:
            print(f"  [WARNING] 案例集构建器初始化失败: {e}")
            _case_kg_builder = None
        
        # 从案例集构建完整知识图谱
        print("从案例集构建知识图谱...")
        try:
            if _graph_rag and _case_kg_builder:
                case_count = _graph_rag.build_and_index_cases()
                print(f"  [OK] 已从 {case_count} 条案例构建知识图谱")
            else:
                print("  [WARNING] 跳过案例图谱构建")
        except Exception as e:
            print(f"  [WARNING] 案例图谱构建失败: {e}")
        
        # 将各组件传递给知识库
        if _knowledge_base:
            if _postgis_db:
                _knowledge_base.set_postgis_db(_postgis_db)
                print("  [OK] 知识库已关联 PostGIS 数据库")
            if _graph_store:
                _knowledge_base.set_graph_store(_graph_store)
                print("  [OK] 知识库已关联内存图存储")
            if _graph_rag:
                _knowledge_base.set_graph_rag(_graph_rag)
                print("  [OK] 知识库已关联 GraphRAG 引擎")
            if _local_llm:
                _knowledge_base.set_llm(_local_llm)
                print("  [OK] 知识库已关联本地大模型")
        
        # 将数据提供者和增强版数据获取器传递给动态知识图谱构建器
        print("初始化动态知识图谱构建器...")
        try:
            from knowledge_graph.dynamic_builder import get_dynamic_builder
            dynamic_builder = get_dynamic_builder()
            if _data_provider:
                dynamic_builder.set_data_provider(_data_provider)
                print("  [OK] 动态知识图谱构建器已关联数据提供者")
            if _enhanced_data_fetcher:
                dynamic_builder.set_enhanced_data_fetcher(_enhanced_data_fetcher)
                print("  [OK] 动态知识图谱构建器已关联增强版数据获取器")
        except Exception as kg_error:
            print(f"  [WARNING] 动态知识图谱构建器关联失败: {kg_error}")
        
        print("初始化空间风险集成模块...")
        try:
            _spatial_risk_integration = get_spatial_risk_integration(AMAP_KEY)
            print("  [OK] 空间风险集成模块就绪（含增强空间数据）")
        except Exception as sri_error:
            print(f"  [WARNING] 空间风险集成模块初始化失败: {sri_error}")
            import traceback
            traceback.print_exc()
            _spatial_risk_integration = None
        
        _new_system_initialized = True
        print("=" * 80)
        print("新系统初始化完成！")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"[WARNING] 新系统初始化失败: {e}")
        import traceback
        traceback.print_exc()
        print("将继续使用原有系统功能")
        print("=" * 80)
        return False


def build_default_knowledge_graph(builder):
    """构建默认知识图谱（使用AHP动态权重）"""
    from mcp_tools.ahp_weight_calculator import get_ahp_calculator
    
    ahp_calc = get_ahp_calculator()
    ahp_weights = ahp_calc.get_default_weights()
    
    default_factors = [
        ("人口密度", "demographic", ahp_weights["人口密度"] * 100, 0.5),
        ("建筑物密度", "infrastructure", ahp_weights["建筑物密度"] * 100, 0.6),
        ("空中交通", "airspace", ahp_weights["空中交通"] * 100, 0.4),
        ("天气条件", "environmental", ahp_weights["天气条件"] * 100, 0.3),
        ("地理拓扑", "geographic", ahp_weights["地理拓扑"] * 100, 0.5)
    ]
    
    for name, ftype, weight, value in default_factors:
        builder.add_risk_factor(name, ftype, weight, value)
    
    # 从城市数据中心获取基础设施和敏感区域（不再使用硬编码数据）
    city_names = ["武汉", "北京", "上海", "广州", "深圳", "成都", "杭州", "南京"]
    for city in city_names:
        city_info = CHINA_CITY_DATA.get(city, {})
        if city_info:
            builder.add_city_node(city, city_info)
            if city_info.get('num_airports', 0) > 0:
                builder.add_infrastructure(f"{city}机场", "airport", [114.3055, 30.5931])
            if city_info.get('has_sensitive_facilities', False):
                builder.add_sensitive_area(f"{city}敏感区域", "government", 1)


def initialize_vector_database(index_manager):
    """初始化向量数据库，添加低空空域专业知识文档"""
    docs = [
        "低空空域通常指海拔高度1000米以下的空域，是通用航空活动的主要区域。低空空域风险评估需要考虑人口密度、建筑物高度、天气条件、空中交通等多种因素。",
        "人口密度是低空空域风险评估的关键因素。人口密集区域（如城市中心）一旦发生飞行事故，后果将非常严重。通常人口密度超过5000人/平方公里的区域被视为高风险区域。",
        "建筑物高度对低空空域飞行安全有重要影响。超高层建筑（高度超过100米）会显著限制可用空域，增加碰撞风险。飞行区域内最高建筑物的高度是制定安全飞行高度的重要参考。",
        "天气条件直接影响低空空域飞行安全。能见度低于1公里、风速超过15米/秒、有雷雨或强降水等恶劣天气条件下，应禁止或限制低空飞行活动。",
        "敏感区域包括政府机关、军事设施、机场净空区、核电站、大型水库等。在这些区域附近进行低空飞行需要特别审批或完全禁止。"
    ]
    
    index_manager.add_knowledge_documents(
        documents=docs,
        doc_type="knowledge",
        source="system_initialization"
    )


def get_new_system_status():
    """获取新系统状态"""
    status = {
        "new_system_available": _new_system_initialized,
        "knowledge_graph": {
            "entities_count": len(_knowledge_graph.entities) if _knowledge_graph else 0,
            "relations_count": len(_knowledge_graph.relations) if _knowledge_graph else 0
        } if _knowledge_graph else None,
        "vector_db": {
            "documents_count": _vector_db['client'].count() if _vector_db else 0
        } if _vector_db else None,
        "workflow_modes": [m.value for m in _workflow_controller.get_available_modes().keys()] if _workflow_controller else [],
        "mcp_tools": list(_mcp_tools.keys()) if _mcp_tools else [],
        "lora_system": {
            "available": _lora_trainer is not None,
            "trained_models": _lora_trainer.list_trained_models() if _lora_trainer else []
        },
        "real_data_generator": {
            "available": _real_data_generator is not None
        } if _real_data_generator else None,
        "local_inference": {
            "available": _local_inference is not None,
            "latest_model": _local_inference.get_latest_model() if _local_inference else None
        } if _local_inference else None,
        "spatial_risk_integration": {
            "available": _spatial_risk_integration is not None
        } if _spatial_risk_integration else None,
        "graph_store": {
            "available": _graph_store.available if _graph_store else False,
            "statistics": _graph_store.get_statistics() if (_graph_store and _graph_store.available) else None
        },
        "graph_rag": {
            "available": _graph_rag.available if _graph_rag else False,
            "llm_available": _graph_rag.llm_available if _graph_rag else False
        },
        "local_llm": {
            "available": _local_llm.available if _local_llm else False
        },
        "case_kg_builder": {
            "available": _case_kg_builder is not None,
            "cases_loaded": len(_case_kg_builder.get_cases()) if _case_kg_builder else 0
        }
    }
    return status


def get_administrative_district(key, keywords, subdistrict=0):
    cache_key = f"{keywords}_{subdistrict}"
    with cache_lock:
        if cache_key in amap_cache:
            print(f"使用缓存的行政区划数据: {keywords}")
            return amap_cache[cache_key]
    
    url = f"https://restapi.amap.com/v3/config/district?key={key}&keywords={urllib.parse.quote(keywords)}&subdistrict={subdistrict}&extensions=all"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('status') == '1' and data.get('districts'):
                result = data['districts'][0]
                with cache_lock:
                    amap_cache[cache_key] = result
                return result
    except Exception as e:
        print(f"获取行政区划数据失败: {str(e)}")
    return None


def get_subdistrict_detail(key, subdistrict_name, city_name):
    cache_key = f"sub_{subdistrict_name}"
    with cache_lock:
        if cache_key in amap_cache:
            print(f"使用缓存的子区域数据: {subdistrict_name}")
            return amap_cache[cache_key]
    
    search_keywords = subdistrict_name
    url = f"https://restapi.amap.com/v3/config/district?key={key}&keywords={urllib.parse.quote(search_keywords)}&subdistrict=0&extensions=all"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('status') == '1' and data.get('districts'):
                result = data['districts'][0]
                with cache_lock:
                    amap_cache[cache_key] = result
                return result
    except Exception as e:
        print(f"获取子区域{search_keywords}边界失败: {str(e)}")
    return None


def get_administrative_district_multi(keywords, subdistrict=0):
    """使用多种国内API获取行政区划数据（优先使用多地图API管理器）"""
    print(f"使用多地图API管理器获取: {keywords}")
    try:
        multi_map = get_multi_map_api(amap_key=AMAP_KEY, tianditu_key=TIANDITU_KEY)
        result, api_used = multi_map.get_administrative_boundary(keywords, subdistrict, 'all')
        if result:
            print(f"多地图API管理器成功获取: {keywords}, 使用API: {api_used}")
            api_name_map = {
                'amap': 'enhanced_amap',
                'baidu': 'baidu_map',
                'tencent': 'tencent_map',
                'tianditu': 'tianditu'
            }
            return result, api_name_map.get(api_used, api_used)
    except Exception as e:
        print(f"多地图API管理器失败: {str(e)}")
    
    print(f"尝试传统高德地图API获取: {keywords}")
    result = get_administrative_district(AMAP_KEY, keywords, subdistrict)
    if result:
        print(f"高德地图API成功获取: {keywords}")
        return result, 'amap'
    
    print(f"无法获取行政区划数据: {keywords}")
    return None, None


def fetch_subdistrict_detail_wrapper(sub_name, city_name):
    """获取子区域详情 - 使用增强型GIS工具（PostGIS优先→API兜底）"""
    try:
        enhanced_gis = get_enhanced_gis_tool(AMAP_KEY)
        if get_postgis_database:
            try:
                pg_db = get_postgis_database()
                enhanced_gis = get_enhanced_gis_tool(AMAP_KEY, pg_db)
            except Exception as e:
                print(f"[SubDetail] PostGIS不可用，仅使用API: {e}")
        result = enhanced_gis.get_administrative_boundary(sub_name, 0, 'all', city_name=city_name)
        if result:
            return (sub_name, result)
    except Exception as e:
        print(f"增强型GIS工具获取子区域失败: {sub_name}, {str(e)}")
    
    return (sub_name, get_subdistrict_detail(AMAP_KEY, sub_name, city_name))


def get_weather_data(city_name):
    """获取指定城市的天气数据（使用高德地图天气API）"""
    try:
        geocode_url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_KEY}&address={urllib.parse.quote(city_name)}"
        print(f"调用地理编码API: {geocode_url}")
        with urllib.request.urlopen(geocode_url, timeout=10) as response:
            geocode_data = json.loads(response.read().decode('utf-8'))
            print(f"地理编码API返回: {geocode_data}")
            
            if geocode_data.get('status') == '1' and geocode_data.get('geocodes'):
                adcode = geocode_data['geocodes'][0].get('adcode', '')
                if adcode:
                    weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_KEY}&city={adcode}&extensions=base"
                    print(f"调用天气API: {weather_url}")
                    with urllib.request.urlopen(weather_url, timeout=10) as weather_resp:
                        weather_data = json.loads(weather_resp.read().decode('utf-8'))
                        print(f"天气API返回: {weather_data}")
                        
                        if weather_data.get('status') == '1' and weather_data.get('lives'):
                            live = weather_data['lives'][0]
                            result = {
                                "city": city_name,
                                "condition": live.get('weather', '未知'),
                                "temperature": f"{live.get('temperature', 'N/A')}°C",
                                "wind_speed": f"{live.get('windpower', 'N/A')}级",
                                "visibility": f"{live.get('visibility', 'N/A')}km",
                                "humidity": f"{live.get('humidity', 'N/A')}%",
                                "source": "高德地图天气API"
                            }
                            return result
    except Exception as e:
        print(f"获取天气数据失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return {
        "city": city_name,
        "condition": "未知",
        "temperature": "N/A",
        "wind_speed": "N/A",
        "visibility": "N/A",
        "humidity": "N/A",
        "source": "API不可用"
    }


def search_city_info(city_name):
    """搜索城市相关信息（使用高德地图API）"""
    url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_KEY}&address={urllib.parse.quote(city_name)}"
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
        if data.get('status') == '1' and data.get('geocodes'):
            geocode = data['geocodes'][0]
            location = geocode.get('location', '').split(',')
            lng, lat = location if len(location) == 2 else ('', '')
            
            result = {
                "city": city_name,
                "latitude": lat,
                "longitude": lng,
                "type": geocode.get('level', '城市'),
                "country": geocode.get('country', ''),
                "province": geocode.get('province', ''),
                "display_name": geocode.get('formatted_address', ''),
                "source": "高德地图地理编码API"
            }
            return json.dumps(result, ensure_ascii=False)
    
    raise Exception(f"无法获取{city_name}的城市信息")


def get_traffic_data(city_name):
    """获取城市交通数据（使用高德地图API）"""
    geocode_url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_KEY}&address={urllib.parse.quote(city_name)}"
    with urllib.request.urlopen(geocode_url, timeout=10) as response:
        geocode_data = json.loads(response.read().decode('utf-8'))
        
        if geocode_data.get('status') == '1' and geocode_data.get('geocodes'):
            location = geocode_data['geocodes'][0].get('location', '116.397428,39.90923')
            url = f"https://restapi.amap.com/v3/traffic/status/circle?key={AMAP_KEY}&location={location}&radius=2000"
            with urllib.request.urlopen(url, timeout=10) as traffic_resp:
                data = json.loads(traffic_resp.read().decode('utf-8'))
                
                traffic_data = {
                    "city": city_name,
                    "status": data.get('status', '0'),
                    "info": data.get('info', ''),
                    "traffic_info": data.get('trafficinfo', {}),
                    "source": "高德地图API"
                }
                return json.dumps(traffic_data, ensure_ascii=False)
    
    raise Exception(f"无法获取{city_name}的交通数据")


def calculate_haversine_distance(point1_lng, point1_lat, point2_lng, point2_lat):
    """计算两点之间的Haversine距离"""
    from mcp_tools.gis_spatial_operators import Point
    gis_ops = get_gis_spatial_operators()
    p1 = Point(lng=point1_lng, lat=point1_lat)
    p2 = Point(lng=point2_lng, lat=point2_lat)
    distance = gis_ops.calculate_haversine_distance(p1, p2)
    return json.dumps({"distance_km": round(distance, 2)}, ensure_ascii=False)

def analyze_spatial_relationship(point_lng, point_lat, polygon_coordinates, distance_threshold_km=5.0):
    """分析点与多边形的空间关系"""
    from mcp_tools.gis_spatial_operators import Point, Polygon
    gis_ops = get_gis_spatial_operators()
    point = Point(lng=point_lng, lat=point_lat)
    polygon = Polygon(coordinates=polygon_coordinates)
    result = gis_ops.analyze_spatial_relationship(point, polygon, distance_threshold_km)
    return json.dumps(result, ensure_ascii=False)

def assess_environmental_factors(weather_data, terrain_data=None, population_data=None):
    """综合评估环境因子风险"""
    env_processor = get_environmental_factors_processor()
    weather_result = env_processor.process_weather_data(weather_data)
    terrain_result = env_processor.process_terrain_data(terrain_data or {"elevation": 0.0, "complexity": "平坦"})
    population_result = env_processor.process_population_data(population_data or {"density": 1000.0, "urban_level": "中等密度"})
    integrated = env_processor.integrate_all_factors(weather_result, terrain_result, population_result)
    return json.dumps(integrated, ensure_ascii=False)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather_data",
            "description": "获取指定城市的实时天气数据，包括气温、风力、能见度等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、武汉"
                    }
                },
                "required": ["city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_city_info",
            "description": "搜索城市的基本信息，包括城市类型、人口、面积、GDP、主要特点等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、武汉"
                    }
                },
                "required": ["city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_traffic_data",
            "description": "获取城市的交通数据，包括机场数量、航线数量、铁路站点、交通拥堵程度等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、武汉"
                    }
                },
                "required": ["city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_haversine_distance",
            "description": "使用Haversine公式计算两个地理坐标点之间的球面距离（单位：公里）",
            "parameters": {
                "type": "object",
                "properties": {
                    "point1_lng": {"type": "number", "description": "第一个点的经度"},
                    "point1_lat": {"type": "number", "description": "第一个点的纬度"},
                    "point2_lng": {"type": "number", "description": "第二个点的经度"},
                    "point2_lat": {"type": "number", "description": "第二个点的纬度"}
                },
                "required": ["point1_lng", "point1_lat", "point2_lng", "point2_lat"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_spatial_relationship",
            "description": "分析一个点与多边形的空间关系，包括是否在多边形内、距离、面积、风险等级等",
            "parameters": {
                "type": "object",
                "properties": {
                    "point_lng": {"type": "number", "description": "点的经度"},
                    "point_lat": {"type": "number", "description": "点的纬度"},
                    "polygon_coordinates": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}, "description": "多边形坐标列表"},
                    "distance_threshold_km": {"type": "number", "description": "距离阈值，默认5.0公里"}
                },
                "required": ["point_lng", "point_lat", "polygon_coordinates"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assess_environmental_factors",
            "description": "综合评估天气、地形、人口密度等环境因子的风险等级",
            "parameters": {
                "type": "object",
                "properties": {
                    "weather_data": {"type": "object", "description": "天气数据，包含condition、temperature、humidity、wind_speed"},
                    "terrain_data": {"type": "object", "description": "地形数据，包含elevation、complexity（可选）"},
                    "population_data": {"type": "object", "description": "人口数据，包含density、urban_level（可选）"}
                },
                "required": ["weather_data"]
            }
        }
    }
]

AVAILABLE_FUNCTIONS = {
    "get_weather_data": get_weather_data,
    "search_city_info": search_city_info,
    "get_traffic_data": get_traffic_data,
    "calculate_haversine_distance": calculate_haversine_distance,
    "analyze_spatial_relationship": analyze_spatial_relationship,
    "assess_environmental_factors": assess_environmental_factors
}


def get_polyline_coordinates(polyline_str):
    coordinates = []
    for ring in polyline_str.split('|'):
        ring_coords = []
        for point in ring.split(';'):
            lng, lat = point.split(',')
            ring_coords.append([float(lng), float(lat)])
        coordinates.append(ring_coords)
    return coordinates


def generate_improved_polygon(center_lng, center_lat, lng_min, lng_max, lat_min, lat_max, area_name=None):
    """
    生成改进的区域多边形，避免简单的正方形
    根据城市轮廓特点生成更自然的形状
    """
    # 计算中心点和边界
    width = lng_max - lng_min
    height = lat_max - lat_min
    center_lng = (lng_min + lng_max) / 2
    center_lat = (lat_min + lat_max) / 2
    
    num_points = 8
    polygon = []
    
    for i in range(num_points):
        angle = (2 * math.pi * i) / num_points - math.pi / 8
        lng = center_lng + width * 0.45 * math.cos(angle)
        lat = center_lat + height * 0.45 * math.sin(angle) * 0.85
        polygon.append([lng, lat])
    
    polygon.append(polygon[0])
    return polygon


def get_better_rectangle(center_lng, center_lat, offset=0.05, area_name=None):
    """
    获取改进的矩形区域，带有圆角效果
    """
    polygon = []
    corner_radius = offset * 0.2
    
    corners = [
        (center_lng - offset + corner_radius, center_lat - offset + corner_radius),
        (center_lng + offset - corner_radius, center_lat - offset + corner_radius),
        (center_lng + offset - corner_radius, center_lat + offset - corner_radius),
        (center_lng - offset + corner_radius, center_lat + offset - corner_radius)
    ]
    
    for i, (cx, cy) in enumerate(corners):
        start_angle = (i + 1) * math.pi / 2
        end_angle = (i + 2) * math.pi / 2
        num_corner_points = 4
        
        for j in range(num_corner_points):
            angle = start_angle + (end_angle - start_angle) * j / num_corner_points
            lng = cx + corner_radius * math.cos(angle)
            lat = cy + corner_radius * math.sin(angle)
            polygon.append([lng, lat])
    
    polygon.append(polygon[0])
    return polygon


def call_deepseek_api(system_content, user_content, max_tokens=1500, use_cache=True, use_tools=False, timeout=120):
    cache_key = f"{hash(system_content + user_content + str(use_tools))}"
    used_tools = []
    if use_cache:
        with cache_lock:
            if cache_key in deepseek_cache:
                print(f"使用缓存的DeepSeek结果")
                cached_result = deepseek_cache[cache_key]
                return cached_result, used_tools
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_KEY}"
    }
    
    messages = [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": user_content
        }
    ]
    
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    
    if use_tools:
        data["tools"] = TOOLS
    
    try:
        encoded_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, encoded_data, headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            assistant_message = result['choices'][0]['message']
            
            if use_tools and 'tool_calls' in assistant_message and assistant_message['tool_calls']:
                print("DeepSeek需要调用工具，执行工具调用...")
                tool_calls = assistant_message['tool_calls']
                
                messages.append(assistant_message)
                
                for tool_call in tool_calls:
                    function_name = tool_call['function']['name']
                    function_args = json.loads(tool_call['function']['arguments'])
                    tool_call_id = tool_call['id']
                    
                    print(f"调用工具: {function_name}，参数: {function_args}")
                    used_tools.append(function_name)
                    
                    if function_name in AVAILABLE_FUNCTIONS:
                        function_response = AVAILABLE_FUNCTIONS[function_name](**function_args)
                        
                        messages.append({
                            "role": "tool",
                            "content": function_response,
                            "tool_call_id": tool_call_id
                        })
                    else:
                        print(f"未知的工具: {function_name}")
                
                print("工具调用完成，重新请求DeepSeek...")
                data["messages"] = messages
                if "tools" in data:
                    del data["tools"]
                
                encoded_data = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, encoded_data, headers)
                with urllib.request.urlopen(req, timeout=45) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    content = result['choices'][0]['message']['content']
            else:
                content = assistant_message.get('content', '')
            
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_content = content[json_start:json_end]
                    parsed_result = json.loads(json_content)
                else:
                    parsed_result = json.loads(content)
                
                with cache_lock:
                    deepseek_cache[cache_key] = parsed_result
                return parsed_result, used_tools
            except Exception as e:
                print(f"JSON解析失败: {str(e)}，原始内容: {content[:200]}")
                return None, used_tools
    except Exception as e:
        print(f"DeepSeek API调用失败: {str(e)}")
        return None, used_tools


def get_city_specific_factors(city_name):
    """
    获取城市特定的风险评估因素（使用AHP+LLM动态权重）
    """
    from mcp_tools.ahp_weight_calculator import get_ahp_calculator
    from mcp_tools.llm_weight_adjuster import get_llm_weight_adjuster
    
    ahp_calc = get_ahp_calculator()
    llm_adjuster = get_llm_weight_adjuster(local_llm_client=_local_llm if '_local_llm' in dir() else None)
    
    city_data = {}
    if _data_provider:
        try:
            city_info = _data_provider.get_city_info(city_name)
            if city_info:
                city_data = {
                    'population_density': city_info.get('population_density', 2000),
                    'building_density': city_info.get('building_density', 0.5),
                    'num_airports': city_info.get('num_airports', 1),
                    'avg_wind_speed': city_info.get('avg_wind_speed', 5.0),
                    'terrain_complexity': city_info.get('terrain_complexity', 0.5),
                    'has_typhoon': city_info.get('has_typhoon', False),
                    'has_mountains': city_info.get('has_mountains', False),
                    'geo_topology_score': city_info.get('geo_topology_score', 0.5),
                    'has_sensitive_facilities': city_info.get('has_sensitive_facilities', False),
                    'area_km2': city_info.get('area_km2', 5000),
                    'annual_flights': city_info.get('annual_flights', 50000)
                }
        except Exception as e:
            print(f"[WARNING] 获取城市数据失败: {e}")
    
    base_weights = ahp_calc.get_default_weights()
    adjusted_weights = llm_adjuster.adjust_weights_by_llm(base_weights, city_data)
    weight_report = llm_adjuster.generate_weight_report(base_weights, adjusted_weights, city_data)
    
    factors = [
        {"name": "人口密度", "weight": round(adjusted_weights["人口密度"] * 100, 1), "description": "区域人口密集程度，影响事故后果"},
        {"name": "建筑物密度", "weight": round(adjusted_weights["建筑物密度"] * 100, 1), "description": "建筑物分布密度和高度"},
        {"name": "空中交通", "weight": round(adjusted_weights["空中交通"] * 100, 1), "description": "航线密集度、飞行高度层"},
        {"name": "天气", "weight": round(adjusted_weights["天气条件"] * 100, 1), "description": "包括降水、能见度、风速等气象条件"},
        {"name": "地理拓扑", "weight": round(adjusted_weights["地理拓扑"] * 100, 1), "description": "地理拓扑因素，评估飞行航线与周边重要设施的空间邻近程度"}
    ]
    
    return {
        "factors": factors,
        "city_analysis": f"{city_name}的AHP+LLM动态权重风险评估分析",
        "weight_method": "AHP层次分析法 + LLM动态调整",
        "weight_report": weight_report,
        "used_tools": ["AHP权重计算器", "LLM权重调整器"],
        "city_data": city_data
    }


def evaluate_all_districts_with_deepseek(region_name, districts_info, factors, city_center):
    system_content = """你是一个专业的低空空域风险评估专家。请根据提供的评估因素，对一个城市的多个区县进行风险评估。

风险等级分为：低风险、较低风险、中等风险、较高风险、极高风险。

请为每个区县返回：
- risk_level: 风险等级（5选一）
- explanation: 简要评估说明（100字以内）
- key_factors: 主要影响因素列表（2-3个最关键因素的名称）

请返回JSON格式，结构为：
{
  "results": {
    "区县名称1": {
      "risk_level": "风险等级",
      "explanation": "说明",
      "key_factors": ["因素1", "因素2"]
    },
    "区县名称2": {
      ...
    }
  }
}"""

    districts_list = [f"- {d['name']}: 中心坐标{d['center']}" for d in districts_info]
    user_content = f"""请对'{region_name}'的以下区县进行风险评估：

{chr(10).join(districts_list)}

评估因素及权重：
{json.dumps(factors, ensure_ascii=False, indent=2)}

城市中心位置：{city_center}

请根据每个区县的特点和评估因素进行综合分析。"""

    result, used_tools = call_deepseek_api(system_content, user_content, max_tokens=3000, use_tools=False, timeout=180)
    
    if result and 'results' in result:
        return result['results'], used_tools
    
    return {}, []


def evaluate_region(region, input_processing=None):
    default_center = [30.5928, 114.3055]
    center_lat, center_lng = default_center
    
    lat_min = center_lat - 0.2
    lat_max = center_lat + 0.2
    lng_min = center_lng - 0.25
    lng_max = center_lng + 0.25
    
    all_used_tools = []
    environmental_assessment = None
    sora_assessment_result = None
    llm_assessment_result = None
    city_real_data = None
    
    print(f"调用get_administrative_district_multi...")
    district, api_used = get_administrative_district_multi(region, subdistrict=2)
    
    if district and 'districts' in district and len(district['districts']) == 1:
        print(f"尝试查询更详细的子区域数据...")
        sub_name = district['districts'][0].get('name', '')
        if sub_name:
            district, _ = get_administrative_district_multi(sub_name, subdistrict=1)
    
    print(f"district is None: {district is None}")
    
    risk_areas = []
    city_coordinates = []
    
    if district:
        print(f"成功获取{region}行政区划数据")
        if 'center' in district:
            center_lng, center_lat = map(float, district['center'].split(','))
            print(f"城市中心: {center_lng}, {center_lat}")
        
        # 调用环境因子处理模块获取环境风险评估
        print(f"正在获取{region}天气数据用于环境因子评估...")
        weather_data = get_weather_data(region)
        print(f"天气数据: {weather_data}")
        
        # 准备环境因子数据
        env_weather_data = {
            "condition": weather_data.get("condition", "未知"),
            "temperature": weather_data.get("temperature", 0),
            "humidity": weather_data.get("humidity", 0),
            "wind_speed": weather_data.get("wind_speed", 0)
        }
        
        # 调用环境因子处理模块
        env_processor = get_environmental_factors_processor()
        environmental_assessment = None
        try:
            environmental_result = json.loads(assess_environmental_factors(env_weather_data))
            environmental_assessment = environmental_result
            print(f"环境因子综合评估完成: {environmental_assessment.get('overall_risk_level', '未知')}")
            all_used_tools.append('assess_environmental_factors')
        except Exception as e:
            print(f"环境因子评估失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # SORA风险评估
        print(f"正在执行SORA风险评估...")
        try:
            sora_assessor = get_sora_assessor()
            
            weather_wind_speed = weather_data.get("wind_speed", 5.0)
            if isinstance(weather_wind_speed, str):
                try:
                    weather_wind_speed = float(weather_wind_speed.replace('km/h', '').strip())
                    weather_wind_speed = weather_wind_speed / 3.6
                except:
                    weather_wind_speed = 5.0
            
            weather_precipitation = 0.0
            weather_condition = weather_data.get("condition", "晴")
            if "雨" in str(weather_condition):
                weather_precipitation = 5.0
            if "大雨" in str(weather_condition) or "暴雨" in str(weather_condition):
                weather_precipitation = 15.0
            
            weather_temp = weather_data.get("temperature", 20)
            if isinstance(weather_temp, str):
                try:
                    weather_temp = float(weather_temp.replace('°C', '').replace('℃', '').strip())
                except:
                    weather_temp = 20
            
            has_thunderstorm = "雷" in str(weather_condition)
            visibility_km = 10.0
            if "雾" in str(weather_condition) or "霾" in str(weather_condition):
                visibility_km = 3.0
            if "大雾" in str(weather_condition):
                visibility_km = 1.0
            
            population_density = 500.0
            if _data_provider:
                try:
                    pop_data = _data_provider.get_population_data(region)
                    if pop_data:
                        population_density = pop_data.get('density', 500.0)
                except:
                    pass
            
            if population_density <= 500.0:
                try:
                    city_pop_map = {
                        '北京': 1300, '上海': 3800, '广州': 2500, '深圳': 8000,
                        '杭州': 1300, '南京': 1800, '成都': 1100, '武汉': 1200,
                        '西安': 900, '重庆': 380, '天津': 1100, '苏州': 1200,
                        '长沙': 1400, '青岛': 1000, '大连': 800, '厦门': 2000
                    }
                    for city, density in city_pop_map.items():
                        if city in region:
                            population_density = density
                            break
                except:
                    pass
            
            airport_proximity_km = 50.0
            has_air_traffic = False
            try:
                city_airport_map = {
                    '北京': 25.0, '上海': 30.0, '广州': 28.0, '深圳': 32.0,
                    '成都': 18.0, '西安': 20.0, '武汉': 22.0, '南京': 35.0,
                    '杭州': 25.0, '重庆': 15.0, '天津': 20.0
                }
                for city, dist in city_airport_map.items():
                    if city in region:
                        airport_proximity_km = dist
                        has_air_traffic = True
                        break
            except:
                pass
            
            sora_ground_data = GroundRiskData(
                population_density=population_density,
                building_density=population_density / 2000.0,
                critical_infrastructure=[],
                is_residential=population_density > 1000,
                is_commercial=population_density > 500,
            )
            
            sora_air_data = AirRiskData(
                airspace_altitude_agl_m=100.0,
                is_isolated_airspace=False,
                is_controlled_airspace=has_air_traffic,
                is_flyable_airspace=not has_air_traffic,
                airport_proximity_km=airport_proximity_km,
                other_aircraft_traffic=has_air_traffic,
                night_operation=False,
                visibility_km=visibility_km,
            )
            
            sora_natural_data = NaturalEnvironmentData(
                wind_speed_ms=weather_wind_speed,
                precipitation_mm_h=weather_precipitation,
                temperature_c=weather_temp,
                thunderstorm=has_thunderstorm,
                visibility_km=visibility_km,
            )
            
            sora_topology_data = TopologyData(
                terrain_elevation_m=50.0 + (population_density / 100),
                terrain_complexity=0.3 + (population_density / 5000),
                has_mountains=any(x in region for x in ['重庆', '成都', '西安', '山']),
                has_water_bodies=any(x in region for x in ['武汉', '南京', '上海', '杭州', '江', '河', '湖', '海']),
            )
            
            sora_assessment_result = sora_assessor.assess(
                sora_ground_data, sora_air_data,
                sora_natural_data, sora_topology_data
            )
            
            print(f"SORA评估完成: SAIL={sora_assessment_result['sora_assessment']['sail_level']}, "
                  f"风险等级={sora_assessment_result['risk_level']}, "
                  f"综合评分={sora_assessment_result['final_risk_score']}")
            all_used_tools.append('sora_risk_assessment')
            
            # LLM辅助评估（本地LLM优先，模板化回退）
            print(f"正在执行LLM辅助评估...")
            try:
                llm_assessor = get_llm_risk_assessor(
                    local_llm_client=_local_llm if '_local_llm' in dir() else None
                )
                city_data = CHINA_CITY_DATA.get(region, {})
                
                graph_context = None
                if _new_system_initialized and _graph_rag:
                    try:
                        from knowledge_graph.graph_rag import get_graph_rag
                        rag = get_graph_rag()
                        graph_context = rag.query_risk_context(region)
                    except Exception:
                        pass
                
                llm_assessment_result = llm_assessor.assess_risk_with_llm(
                    region=region,
                    sora_result=sora_assessment_result,
                    weighted_result=sora_assessment_result,
                    environmental_factors=environmental_assessment or {},
                    city_real_data=city_data,
                    weight_report="",
                    graph_context=graph_context
                )
                
                if llm_assessment_result.get('available'):
                    print(f"LLM评估完成: 风险等级={llm_assessment_result['llm_risk_level']}, "
                          f"评分={llm_assessment_result['llm_risk_score']}, "
                          f"提供商={llm_assessment_result.get('api_provider', 'unknown')}")
                    all_used_tools.append('llm_risk_assessment')
                else:
                    print(f"LLM评估不可用: {llm_assessment_result.get('message', '无模型')}")
            except Exception as e:
                print(f"LLM评估失败: {str(e)}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"SORA评估失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        if 'polyline' in district and district['polyline']:
            city_coords_list = get_polyline_coordinates(district['polyline'])
            if city_coords_list:
                city_coordinates = city_coords_list[0]
                lats = [coord[1] for coord in city_coordinates]
                lngs = [coord[0] for coord in city_coordinates]
                lat_min, lat_max = min(lats), max(lats)
                lng_min, lng_max = min(lngs), max(lngs)
                print(f"更新后的城市边界: lat[{lat_min}, {lat_max}], lng[{lng_min}, {lng_max}]")
        else:
            lat_min = center_lat - 0.2
            lat_max = center_lat + 0.2
            lng_min = center_lng - 0.25
            lng_max = center_lng + 0.25
            city_coordinates = [[lng_min, lat_min], [lng_min, lat_max], [lng_max, lat_max], [lng_max, lat_min]]
        
        if _new_system_initialized and _workflow_controller:
            print("执行工作流获取增强上下文...")
            try:
                # 使用当前城市的动态知识图谱
                dynamic_builder = get_dynamic_builder()
                city_kg = dynamic_builder.build_for_city(region, use_llm=False)
                
                # 创建临时的提取器和工作流
                temp_extractor = StructuredInfoExtractor(city_kg)
                temp_workflow = RiskAssessmentWorkflow(
                    knowledge_extractor=temp_extractor,
                    vector_retriever=_vector_retriever
                )
                
                workflow_result = temp_workflow.execute(
                    mode=WorkflowMode.STANDARD,
                    region=region
                )
                print(f"工作流执行完成: {workflow_result}")
            except Exception as e:
                print(f"工作流执行失败，使用默认工作流: {e}")
                import traceback
                traceback.print_exc()
                # 回退到默认工作流
                workflow_result = _workflow_controller.execute(
                    mode=WorkflowMode.STANDARD,
                    region=region
                )
                print(f"默认工作流执行完成: {workflow_result}")
        
        print(f"正在使用本地模型为{region}制定评估因素...")
        complete_inference = get_complete_inference()
        city_factors_result = complete_inference.generate_city_specific_factors(region)
        factors_with_weights = city_factors_result.get('factors', [])
        city_analysis = city_factors_result.get('city_analysis', '')
        factors_used_tools = city_factors_result.get('used_tools', [])
        all_used_tools.extend(factors_used_tools)
        model_used = city_factors_result.get('model_used', 'base_model')
        print(f"本地模型为{region}制定了{len(factors_with_weights)}个评估因素 (模型: {model_used})")
        
        all_sub_districts = []
        districts_info = []
        
        if 'districts' in district and district['districts']:
            print(f"发现{len(district['districts'])}个下辖区县")
            subdistricts_to_fetch = []
            
            for sub_district in district['districts']:
                sub_name = sub_district.get('name', '')
                print(f"处理区县: {sub_name}")
                
                sub_center_lat, sub_center_lng = center_lat, center_lng
                if 'center' in sub_district:
                    sub_center_lng, sub_center_lat = map(float, sub_district['center'].split(','))
                
                area_polygons = []
                if 'polyline' in sub_district and sub_district['polyline']:
                    area_polygons = get_polyline_coordinates(sub_district['polyline'])
                    print(f"区县{sub_name}从主数据获取到{len(area_polygons)}个边界多边形")
                else:
                    subdistricts_to_fetch.append((sub_name, sub_center_lng, sub_center_lat))
                    area_polygons = []
                
                districts_info.append({
                    'name': sub_name,
                    'center': [sub_center_lng, sub_center_lat]
                })
                
                all_sub_districts.append({
                    'name': sub_name,
                    'center_lat': sub_center_lat,
                    'center_lng': sub_center_lng,
                    'polygons': area_polygons
                })
            
            if subdistricts_to_fetch:
                print(f"并行获取{len(subdistricts_to_fetch)}个子区域的边界数据...")
                with ThreadPoolExecutor(max_workers=min(10, len(subdistricts_to_fetch))) as executor:
                    future_to_sub = {
                        executor.submit(fetch_subdistrict_detail_wrapper, name, region): name 
                        for name, _, _ in subdistricts_to_fetch
                    }
                    
                    sub_detail_map = {}
                    for future in as_completed(future_to_sub):
                        sub_name, sub_detail = future.result()
                        if sub_detail:
                            sub_detail_map[sub_name] = sub_detail
                
                for sub in all_sub_districts:
                    if sub['name'] in sub_detail_map and not sub['polygons']:
                        sub_detail = sub_detail_map[sub['name']]
                        if 'polyline' in sub_detail and sub_detail['polyline']:
                            sub['polygons'] = get_polyline_coordinates(sub_detail['polyline'])
                            print(f"区县{sub['name']}并行获取到{len(sub['polygons'])}个边界多边形")
            
            if len(districts_info) <= 6:
                print(f"正在使用本地模型一次性评估所有{len(districts_info)}个区县...")
                districts_results = complete_inference.evaluate_districts(
                    region, 
                    districts_info, 
                    factors_with_weights, 
                    [center_lng, center_lat]
                )
                district_results = districts_results.get('results', {})
                districts_model_used = districts_results.get('model_used', 'base_model')
                print(f"本地模型评估完成，得到{len(district_results)}个结果 (模型: {districts_model_used})")
                
                for sub in all_sub_districts:
                    sub_name = sub['name']
                    if sub_name in district_results:
                        result = district_results[sub_name]
                        sub['level'] = result.get('risk_level', '中等风险')
                        sub['explanation'] = result.get('explanation', f"{sub_name}区域的风险评估")
                        sub['key_factors'] = result.get('key_factors', [])
                    else:
                        # 使用数据计算风险等级
                        if _data_provider:
                            sub['level'], risk_score = _data_provider.calculate_risk_level(region, sub_name)
                            sub['explanation'] = f"{sub_name}区域的风险评估（基于数据计算）"
                            # 动态找出权重最大的因素作为关键因素
                            if factors_with_weights:
                                sorted_factors = sorted(factors_with_weights, key=lambda x: x.get('weight', 0), reverse=True)
                                sub['key_factors'] = [f["name"] for f in sorted_factors[:2]]
                            else:
                                sub['key_factors'] = ['人口密度', '建筑物密度']
                        else:
                            risk_levels = ['低风险', '较低风险', '中等风险', '较高风险', '极高风险']
                            distance = math.sqrt((sub['center_lat'] - center_lat)**2 + (sub['center_lng'] - center_lng)**2)
                            level_index = min(4, int(distance * 10))
                            sub['level'] = risk_levels[level_index]
                            sub['explanation'] = f"{sub_name}区域的风险评估"
                            sub['key_factors'] = [f["name"] for f in factors_with_weights[:2]] if factors_with_weights else ['人口密度', '建筑物密度']
            else:
                print(f"区县数量较多({len(districts_info)}个)，使用数据评估")
                for sub in all_sub_districts:
                    if _data_provider:
                        sub['level'], risk_score = _data_provider.calculate_risk_level(region, sub['name'])
                        sub['explanation'] = f"{sub['name']}区域的风险评估（基于数据计算）"
                        # 动态找出权重最大的因素作为关键因素
                        if factors_with_weights:
                            sorted_factors = sorted(factors_with_weights, key=lambda x: x.get('weight', 0), reverse=True)
                            sub['key_factors'] = [f["name"] for f in sorted_factors[:2]]
                        else:
                            sub['key_factors'] = ['人口密度', '建筑物密度']
                    else:
                        risk_levels = ['低风险', '较低风险', '中等风险', '较高风险', '极高风险']
                        distance = math.sqrt((sub['center_lat'] - center_lat)**2 + (sub['center_lng'] - center_lng)**2)
                        level_index = min(4, int(distance * 10))
                        sub['level'] = risk_levels[level_index]
                        sub['explanation'] = f"{sub['name']}区域的风险评估"
                        sub['key_factors'] = [f["name"] for f in factors_with_weights[:2]] if factors_with_weights else ['人口密度', '建筑物密度']
        else:
            print("没有下辖区县，创建网格分区")
            lat_step = (lat_max - lat_min) / 3
            lng_step = (lng_max - lng_min) / 3
            risk_levels = ['低风险', '较低风险', '中等风险', '较高风险', '极高风险']
            
            for i in range(3):
                for j in range(3):
                    cell_lat_min = lat_min + i * lat_step
                    cell_lat_max = lat_min + (i + 1) * lat_step
                    cell_lng_min = lng_min + j * lng_step
                    cell_lng_max = lng_min + (j + 1) * lng_step
                    
                    cell_center_lat = (cell_lat_min + cell_lat_max) / 2
                    cell_center_lng = (cell_lng_min + cell_lng_max) / 2
                    
                    cell_name = f"区域{i*3+j+1}"
                    districts_info.append({
                        'name': cell_name,
                        'center': [cell_center_lng, cell_center_lat]
                    })
                    
                    improved_grid_polygon = generate_improved_polygon(
                    cell_center_lng, cell_center_lat,
                    cell_lng_min, cell_lng_max,
                    cell_lat_min, cell_lat_max,
                    cell_name
                )
                all_sub_districts.append({
                    'name': cell_name,
                    'center_lat': cell_center_lat,
                    'center_lng': cell_center_lng,
                    'polygons': [improved_grid_polygon]
                })
            
            print(f"网格区域使用数据评估")
            for sub in all_sub_districts:
                if _data_provider:
                    sub['level'], risk_score = _data_provider.calculate_risk_level(region, sub['name'])
                    sub['explanation'] = f"{sub['name']}区域的风险评估（基于数据计算）"
                    # 动态找出权重最大的因素作为关键因素
                    if factors_with_weights:
                        sorted_factors = sorted(factors_with_weights, key=lambda x: x.get('weight', 0), reverse=True)
                        sub['key_factors'] = [f["name"] for f in sorted_factors[:2]]
                    else:
                        sub['key_factors'] = ['人口密度', '建筑物密度']
                else:
                    distance = math.sqrt((sub['center_lat'] - center_lat)**2 + (sub['center_lng'] - center_lng)**2)
                    level_index = min(4, int(distance * 10))
                    sub['level'] = risk_levels[level_index]
                    sub['explanation'] = f"{sub['name']}区域的风险评估"
                    sub['key_factors'] = [f["name"] for f in factors_with_weights[:2]] if factors_with_weights else ['人口密度', '建筑物密度']
        
        seen_names = set()
        for sub in all_sub_districts:
            if sub['name'] in seen_names:
                continue
            seen_names.add(sub['name'])
            
            print(f"添加区域: {sub['name']}, 风险等级: {sub['level']}")
            
            if sub['polygons'] and len(sub['polygons']) > 0:
                print(f"区县{sub['name']}有{len(sub['polygons'])}个多边形")
                for polygon_idx, polygon in enumerate(sub['polygons']):
                    if len(polygon) >= 3:
                        print(f"  多边形{polygon_idx+1}有{len(polygon)}个点")
                        risk_areas.append({
                            "level": sub['level'],
                            "coordinates": polygon,
                            "name": sub['name'] if polygon_idx == 0 else f"{sub['name']}_{polygon_idx+1}",
                            "type": "district",
                            "explanation": sub.get('explanation', ''),
                            "key_factors": sub.get('key_factors', [])
                        })
            else:
                print(f"区县{sub['name']}没有多边形数据，尝试多API获取行政区划边界...")
                polyline = None
                
                # 尝试1: MultiMapAPI (高德→百度→腾讯→天地图)
                try:
                    multi_map = get_multi_map_api(amap_key=AMAP_KEY, tianditu_key=TIANDITU_KEY)
                    polyline = multi_map.try_all_apis_for_polyline(sub['name'])
                except Exception as e:
                    print(f"  MultiMapAPI尝试失败: {e}")
                
                # 尝试2: 高德子区域API
                if not polyline:
                    try:
                        sub_detail = get_subdistrict_detail(AMAP_KEY, sub['name'], city_name)
                        if sub_detail and sub_detail.get('polyline'):
                            polyline = sub_detail['polyline']
                            print(f"  高德子区域API获取成功: {sub['name']}")
                    except Exception as e:
                        print(f"  高德子区域API失败: {e}")
                
                if polyline:
                    coords = get_polyline_coordinates(polyline)
                    for poly_idx, polygon in enumerate(coords):
                        if len(polygon) >= 3:
                            risk_areas.append({
                                "level": sub['level'],
                                "coordinates": polygon,
                                "name": sub['name'] if poly_idx == 0 else f"{sub['name']}_{poly_idx+1}",
                                "type": "district",
                                "explanation": sub.get('explanation', ''),
                                "key_factors": sub.get('key_factors', [])
                            })
                    print(f"  成功添加{sub['name']}的行政区划边界 ({len(coords)}个多边形)")
                else:
                    print(f"  所有API均无法获取{sub['name']}的边界数据，仅标注中心点")
                    risk_areas.append({
                        "level": sub['level'],
                        "coordinates": [[sub['center_lng'], sub['center_lat']],
                                       [sub['center_lng'] + 0.001, sub['center_lat']],
                                       [sub['center_lng'], sub['center_lat'] + 0.001]],
                        "name": sub['name'],
                        "type": "district",
                        "explanation": sub.get('explanation', ''),
                        "key_factors": sub.get('key_factors', []),
                        "no_boundary": True
                    })
    else:
        print(f"无法获取行政区划数据，使用网格分区")
        
        # 调用环境因子处理模块获取环境风险评估
        print(f"正在获取{region}天气数据用于环境因子评估...")
        weather_data = get_weather_data(region)
        print(f"天气数据: {weather_data}")
        
        # 准备环境因子数据
        env_weather_data = {
            "condition": weather_data.get("condition", "未知"),
            "temperature": weather_data.get("temperature", 0),
            "humidity": weather_data.get("humidity", 0),
            "wind_speed": weather_data.get("wind_speed", 0)
        }
        
        # 调用环境因子处理模块
        env_processor = get_environmental_factors_processor()
        environmental_assessment = None
        try:
            environmental_result = json.loads(assess_environmental_factors(env_weather_data))
            environmental_assessment = environmental_result
            print(f"环境因子综合评估完成: {environmental_assessment.get('overall_risk_level', '未知')}")
            all_used_tools.append('assess_environmental_factors')
        except Exception as e:
            print(f"环境因子评估失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        if _new_system_initialized and _workflow_controller:
            print("执行工作流获取增强上下文...")
            try:
                # 使用当前城市的动态知识图谱
                dynamic_builder = get_dynamic_builder()
                city_kg = dynamic_builder.build_for_city(region, use_llm=False)
                
                # 创建临时的提取器和工作流
                temp_extractor = StructuredInfoExtractor(city_kg)
                temp_workflow = RiskAssessmentWorkflow(
                    knowledge_extractor=temp_extractor,
                    vector_retriever=_vector_retriever
                )
                
                workflow_result = temp_workflow.execute(
                    mode=WorkflowMode.STANDARD,
                    region=region
                )
                print(f"工作流执行完成: {workflow_result}")
            except Exception as e:
                print(f"工作流执行失败，使用默认工作流: {e}")
                import traceback
                traceback.print_exc()
                # 回退到默认工作流
                workflow_result = _workflow_controller.execute(
                    mode=WorkflowMode.STANDARD,
                    region=region
                )
                print(f"默认工作流执行完成: {workflow_result}")
        
        print(f"正在使用本地模型为{region}制定评估因素...")
        complete_inference = get_complete_inference()
        city_factors_result = complete_inference.generate_city_specific_factors(region)
        factors_with_weights = city_factors_result.get('factors', [])
        city_analysis = city_factors_result.get('city_analysis', '')
        factors_used_tools = city_factors_result.get('used_tools', [])
        all_used_tools.extend(factors_used_tools)
        model_used = city_factors_result.get('model_used', 'base_model')
        print(f"本地模型为{region}制定了{len(factors_with_weights)}个评估因素 (模型: {model_used})")
        
        lat_step = (lat_max - lat_min) / 3
        lng_step = (lng_max - lng_min) / 3
        districts_info = []
        all_sub_districts = []
        
        for i in range(3):
            for j in range(3):
                cell_lat_min = lat_min + i * lat_step
                cell_lat_max = lat_min + (i + 1) * lat_step
                cell_lng_min = lng_min + j * lng_step
                cell_lng_max = lng_min + (j + 1) * lng_step
                
                cell_center_lat = (cell_lat_min + cell_lat_max) / 2
                cell_center_lng = (cell_lng_min + cell_lng_max) / 2
                
                cell_name = f"区域{i*3+j+1}"
                districts_info.append({
                    'name': cell_name,
                    'center': [cell_center_lng, cell_center_lat]
                })
                
                improved_grid_polygon = generate_improved_polygon(
                    cell_center_lng, cell_center_lat,
                    cell_lng_min, cell_lng_max,
                    cell_lat_min, cell_lat_max,
                    cell_name
                )
                all_sub_districts.append({
                    'name': cell_name,
                    'center_lat': cell_center_lat,
                    'center_lng': cell_center_lng,
                    'polygons': [improved_grid_polygon]
                })
        
        print(f"正在使用本地模型一次性评估所有{len(districts_info)}个网格区域...")
        districts_results = complete_inference.evaluate_districts(
            region, 
            districts_info, 
            factors_with_weights, 
            [center_lng, center_lat]
        )
        district_results = districts_results.get('results', {})
        districts_model_used = districts_results.get('model_used', 'base_model')
        print(f"本地模型评估完成，得到{len(district_results)}个结果 (模型: {districts_model_used})")
        
        for sub in all_sub_districts:
            sub_name = sub['name']
            if sub_name in district_results:
                result = district_results[sub_name]
                sub['level'] = result.get('risk_level', '中等风险')
                sub['explanation'] = result.get('explanation', f"{sub_name}区域的风险评估")
                sub['key_factors'] = result.get('key_factors', [])
            else:
                risk_levels = ['低风险', '较低风险', '中等风险', '较高风险', '极高风险']
                distance = math.sqrt((sub['center_lat'] - center_lat)**2 + (sub['center_lng'] - center_lng)**2)
                level_index = min(4, int(distance * 10))
                sub['level'] = risk_levels[level_index]
                sub['explanation'] = f"{sub_name}区域的风险评估"
                sub['key_factors'] = [f["name"] for f in factors_with_weights[:2]] if factors_with_weights else ['人口密度', '建筑物密度']
        
        seen_names = set()
        for sub in all_sub_districts:
            if sub['name'] in seen_names:
                continue
            seen_names.add(sub['name'])
            
            print(f"添加网格区域: {sub['name']}, 风险等级: {sub['level']}")
            if sub['polygons'] and len(sub['polygons']) > 0:
                for polygon in sub['polygons']:
                    if len(polygon) >= 3:
                        risk_areas.append({
                            "level": sub['level'],
                            "coordinates": polygon,
                            "name": sub['name'],
                            "type": "grid",
                            "explanation": sub.get('explanation', ''),
                            "key_factors": sub.get('key_factors', [])
                        })
        
        city_coordinates = [[lng_min, lat_min], [lng_min, lat_max], [lng_max, lat_max], [lng_max, lat_min]]
    
    area_count = len(risk_areas)
    district_names = ', '.join([area['name'] for area in risk_areas if 'name' in area])
    explanation = f"{region}地区风险评估完成。{city_analysis}风险评估将{region}分为{area_count}个区域：{district_names}，基于本地模型定制的评估因素综合判断每个区域的风险程度。"
    
    api_name_map = {
        'amap': '高德地图',
        'enhanced_amap': '增强型高德地图',
        'baidu_map': '百度地图',
        'tencent_map': '腾讯地图'
    }
    used_api_name = api_name_map.get(api_used, '未知API')
    
    detailed_process = []
    
    if input_processing:
        detailed_process.append({
            "step": 1,
            "action": "用户输入理解与关键词提取",
            "coordinates": [center_lat, center_lng],
            "detail": f"使用混合方法（正则表达式+关键词匹配+大模型）从用户输入中提取位置关键词。" +
                     f"原始输入: '{input_processing.get('original_input', '')}'。" +
                     f"提取位置: {input_processing.get('extracted_locations', [])}。" +
                     f"确定主位置: {input_processing.get('primary_location', '')}。" +
                     f"提取置信度: {input_processing.get('confidence', 0):.2f}。" +
                     f"用户意图: {input_processing.get('intent', '')}。" +
                     f"提取方法: {input_processing.get('method', '')}"
        })
        step_offset = 1
    else:
        step_offset = 0
    
    detailed_process.extend([
        {
            "step": 1 + step_offset, 
            "action": f"获取{region}地理边界", 
            "coordinates": [center_lat, center_lng],
            "detail": f"使用{used_api_name}行政区划API获取城市行政边界，确定评估范围，确保风险区与城市边缘贴合"
        },
        {
            "step": 2 + step_offset, 
            "action": "获取行政区划边界数据", 
            "coordinates": [center_lat, center_lng],
            "detail": f"调用{used_api_name}API获取详细的区县级行政区划边界，精确到街道级精度"
        },
        {
            "step": 3 + step_offset, 
            "action": "本地模型分析城市特点", 
            "coordinates": [center_lat, center_lng],
            "detail": city_analysis or "本地模型分析该城市的地理、经济、人口等特点"
        },
        {
            "step": 4 + step_offset, 
            "action": "本地模型制定评估因素", 
            "coordinates": [center_lat, center_lng],
            "detail": f"本地模型根据城市特点定制了{len(factors_with_weights)}个评估因素及权重"
        },
        {
            "step": 5 + step_offset, 
            "action": f"将{region}分为{area_count}个区域", 
            "coordinates": [center_lat, center_lng],
            "detail": "优先使用行政区划边界，确保风险区轮廓与行政区划完全贴合"
        },
        {
            "step": 6 + step_offset, 
            "action": "本地模型一次性评估所有区域", 
            "coordinates": [center_lat, center_lng],
            "detail": f"本地模型根据定制的评估因素对所有{area_count}个区域进行一次性综合评估"
        }
    ])
    
    detailed_process.append({
        "step": 7 + step_offset, 
        "action": "使用的国内网络工具库和API说明", 
        "coordinates": [center_lat, center_lng],
        "detail": "本系统全部使用国内可用的工具库和API："
    })
    
    api_list = [
        {
            "name": "多地图API管理器",
            "url": "mcp_tools/multi_map_api.py",
            "purpose": "统一管理多个国内地图API，依次尝试高德、百度、腾讯地图确保获取到边界数据"
        },
        {
            "name": "增强型GIS工具",
            "url": "mcp_tools/enhanced_gis_tools.py",
            "purpose": "提供更可靠的区域边界数据获取，支持多种策略确保获取到边界数据"
        },
        {
            "name": "高德地图行政区划API",
            "url": "https://restapi.amap.com/v3/config/district",
            "purpose": "获取行政区划边界和子区域信息（优先使用）"
        },
        {
            "name": "百度地图行政区划API",
            "url": "https://api.map.baidu.com/api_region_search/v1/",
            "purpose": "获取行政区划边界（高德地图失败时备用）"
        },
        {
            "name": "腾讯地图地理编码API",
            "url": "https://apis.map.qq.com/ws/geocoder/v1/",
            "purpose": "获取行政区划边界（前两个API失败时备用）"
        },
        {
            "name": "高德地图地理编码API",
            "url": "https://restapi.amap.com/v3/geocode/geo",
            "purpose": "获取城市地理坐标和详细地址信息"
        },
        {
            "name": "高德地图交通态势API",
            "url": "https://restapi.amap.com/v3/traffic/status/circle",
            "purpose": "获取城市交通拥堵状况"
        },
        {
            "name": "高德地图天气API",
            "url": "https://restapi.amap.com/v3/weather/weatherInfo",
            "purpose": "获取城市实时天气数据"
        },
        {
            "name": "Hugging Face镜像站",
            "url": "https://hf-mirror.com",
            "purpose": "国内Hugging Face镜像，提供模型和数据集的快速下载"
        },
        {
            "name": "本地LoRA微调模型",
            "url": "local_models/",
            "purpose": "进行智能风险评估分析和评估因素制定（完全本地，无网络依赖）"
        }
    ]
    
    for idx, api in enumerate(api_list, 1):
        detailed_process.append({
            "step": 7 + step_offset + idx, 
            "action": api["name"],
            "coordinates": [center_lat, center_lng],
            "detail": f"接口地址: {api['url']}，用途: {api['purpose']}"
        })
    
    if all_used_tools:
        unique_tools = list(set(all_used_tools))
        tool_descriptions = {
            'get_weather_data': '调用高德地图天气API，获取实时天气数据（气温、湿度、风速、能见度等）',
            'search_city_info': '调用高德地图地理编码API，获取城市详细地理信息',
            'get_traffic_data': '调用高德地图交通态势API，获取城市交通状况'
        }
        tool_info = []
        for tool in unique_tools:
            desc = tool_descriptions.get(tool, tool)
            tool_info.append(f"{tool}: {desc}")
        
        detailed_process.append({
            "step": 7 + step_offset + len(api_list) + 1, 
            "action": "大模型调用的工具", 
            "coordinates": [center_lat, center_lng],
            "detail": f"本次评估中大模型调用了以下工具：{'; '.join(tool_info)}"
        })
    
    detailed_process.append({
        "step": 7 + step_offset + len(api_list) + 2, 
        "action": "风险区轮廓处理策略", 
        "coordinates": [center_lat, center_lng],
        "detail": "1. 优先使用增强型GIS工具获取行政区划边界，支持多种策略（直接查询、简化关键词、查询上级行政区）确保获取到边界数据；2. 当无法获取行政区划边界时，使用增强型GIS工具生成更自然的备用边界（12个顶点，多层扰动）；3. 仅在所有方法都失败时使用网格分区；4. 严格避免出现点风险区，所有风险区都有完整的多边形边界；5. 确保覆盖输入城市的全部区域"
    })
    
    detailed_process.append({
        "step": 7 + step_offset + len(api_list) + 3, 
        "action": "知识图谱构建", 
        "coordinates": [center_lat, center_lng],
        "detail": "基于评估区域构建知识图谱，包含空域区域、风险因素、基础设施、敏感区域、天气数据等实体及其关系"
    })
    
    detailed_process.append({
        "step": 7 + step_offset + len(api_list) + 4, 
        "action": "工作流执行", 
        "coordinates": [center_lat, center_lng],
        "detail": "基于LangChain框架的多模式工作流已执行，支持标准、快速、精确和自定义四种模式"
    })
    
    detailed_process.append({
        "step": 7 + step_offset + len(api_list) + 5, 
        "action": "MCP工具集", 
        "coordinates": [center_lat, center_lng],
        "detail": "集成监控工具、GIS工具、空域管理工具、飞行规划工具、数据库工具、分析工具和访问控制工具"
    })
    
    detailed_process.append({
        "step": 7 + step_offset + len(api_list) + 6, 
        "action": "LoRA微调系统", 
        "coordinates": [center_lat, center_lng],
        "detail": "支持使用知识图谱和本地大模型生成训练数据，并用LoRA技术对模型进行定向优化"
    })
    
    print(f"正在为城市'{region}'构建动态知识图谱...")
    
    if _knowledge_base:
        print(f"尝试从知识库加载'{region}'的知识图谱...")
        existing_kg_dict = _knowledge_base.load_kg(region)
        if existing_kg_dict:
            print(f"  [OK] 从知识库加载到'{region}'的知识图谱")
            city_kg_dict = existing_kg_dict
        else:
            print(f"  知识库中无'{region}'的知识图谱，正在构建...")
            dynamic_builder = get_dynamic_builder()
            city_kg = dynamic_builder.build_for_city(region, use_llm=False)
            city_kg_dict = city_kg.to_dict()
            print(f"  正在保存'{region}'的知识图谱到知识库...")
            _knowledge_base.save_kg(region, city_kg_dict)
            print(f"  [OK] 知识图谱已保存到知识库")
    else:
        print(f"知识库未初始化，直接构建知识图谱")
        dynamic_builder = get_dynamic_builder()
        city_kg = dynamic_builder.build_for_city(region, use_llm=False)
        city_kg_dict = city_kg.to_dict()
    
    knowledge_graph_data = {
        "entities": [],
        "relations": [],
        "risk_factors": factors_with_weights,
        "infrastructure": [],
        "sensitive_areas": []
    }
    
    for entity in city_kg_dict.get("entities", []):
        knowledge_graph_data["entities"].append({
            "id": entity.get("id", ""),
            "type": entity.get("entity_type", ""),
            "name": entity.get("name", ""),
            "properties": entity.get("properties", {})
        })
        
        etype = entity.get("entity_type", "")
        if etype == "infrastructure":
            knowledge_graph_data["infrastructure"].append({
                "name": entity.get("name", ""),
                "type": entity.get("infra_type", ""),
                "location": entity.get("location", [])
            })
        elif etype == "sensitive_area":
            knowledge_graph_data["sensitive_areas"].append({
                "name": entity.get("name", ""),
                "type": entity.get("area_type", ""),
                "priority": entity.get("priority", 2)
            })
    
    for relation in city_kg_dict.get("relations", []):
        knowledge_graph_data["relations"].append({
            "source": relation.get("source_id", ""),
            "target": relation.get("target_id", ""),
            "type": relation.get("relation_type", "")
        })
    
    print(f"动态知识图谱构建完成，包含{len(knowledge_graph_data['entities'])}个实体，{len(knowledge_graph_data['relations'])}个关系")
    
    # 调试输出知识图谱数据
    print("\n=== 知识图谱实体数据 ===")
    for i, entity in enumerate(knowledge_graph_data['entities']):
        print(f"实体 {i}: ID={entity.get('id')}, 类型={entity.get('type')}, 名称={entity.get('name')}")
    
    print("\n=== 知识图谱关系数据 ===")
    for i, relation in enumerate(knowledge_graph_data['relations']):
        print(f"关系 {i}: 源={relation.get('source')}, 目标={relation.get('target')}, 类型={relation.get('type')}")
    
    # 找到城市实体的ID（第一个实体通常是城市）
    city_entity_id = None
    for entity in knowledge_graph_data["entities"]:
        if entity.get("type") == "airspace_region" or entity.get("type") == "city":
            city_entity_id = entity.get("id")
            break
    
    # 添加子区域实体和关系
    for area in risk_areas:
        subregion_id = f"subregion_{area['name']}"
        knowledge_graph_data["entities"].append({
            "id": subregion_id,
            "type": "subdistrict",
            "name": area['name'],
            "properties": {"risk_level": area['level'], "importance": 0.6}
        })
        if city_entity_id:
            knowledge_graph_data["relations"].append({
                "source": city_entity_id,
                "target": subregion_id,
                "type": "contains"
            })
    
    risk_level_map = {
        "低风险": 0,
        "较低风险": 1,
        "中等风险": 2,
        "较高风险": 3,
        "极高风险": 4
    }
    
    reverse_risk_level_map = {v: k for k, v in risk_level_map.items()}
    
    if risk_areas:
        total_score = 0
        for area in risk_areas:
            level = area.get("level", "中等风险")
            total_score += risk_level_map.get(level, 2)
        
        avg_score = total_score / len(risk_areas)
        overall_risk_level = reverse_risk_level_map.get(round(avg_score), "中等风险")
    else:
        overall_risk_level = "中等风险"
    
    if environmental_assessment:
        env_risk_score = environmental_assessment.get('total_risk_score', 0.5)
        env_risk_level = environmental_assessment.get('overall_risk_level', '中等风险')
        print(f"环境因子风险评分: {env_risk_score}, 等级: {env_risk_level}")
        
        env_assessment_text = environmental_assessment.get('integrated_assessment', '')
        if env_assessment_text:
            explanation = f"{explanation}\n\n环境因子评估: {env_assessment_text}"
    
    if sora_assessment_result:
        sora_risk_level = sora_assessment_result['risk_level']
        sora_final_score = sora_assessment_result['final_risk_score']
        sora_sail = sora_assessment_result['sora_assessment']['sail_level']
        sora_ground_level = sora_assessment_result['sora_assessment']['ground_risk_level']
        sora_air_class = sora_assessment_result['sora_assessment']['air_risk_class']
        weighted_validation = sora_assessment_result['weighted_assessment']['weighted_score']
        
        print(f"SORA风险等级: {sora_risk_level}, 综合评分: {sora_final_score}, "
              f"SAIL: {sora_sail}, 地面等级: {sora_ground_level}, 空中等级: {sora_air_class}")
        print(f"加权辅助验证分数: {weighted_validation}")
        
        sora_level_map = {
            "低风险": "低风险",
            "中等风险": "中等风险",
            "高风险": "较高风险",
            "极高风险": "极高风险"
        }
        sora_mapped_level = sora_level_map.get(sora_risk_level, "中等风险")
        
        if sora_final_score >= 0.7:
            overall_risk_level = "极高风险"
        elif sora_final_score >= 0.4:
            if overall_risk_level in ["低风险", "较低风险"]:
                overall_risk_level = "中等风险"
        elif sora_final_score < 0.2:
            if overall_risk_level in ["较高风险", "极高风险"]:
                overall_risk_level = "中等风险"
        
        sora_recs = sora_assessment_result.get('recommendations', [])
        if sora_recs:
            explanation = f"{explanation}\n\nSORA评估建议: " + "; ".join(sora_recs)
        
        try:
            validation = sora_assessor.validate_assessment(sora_assessment_result)
            sora_assessment_result["_validation"] = validation
            if not validation["pass"]:
                print(f"评估验证未通过: 置信度={validation['confidence_metrics']['overall_confidence']}")
        except Exception as e:
            print(f"评估验证执行失败: {e}")
    
    if llm_assessment_result and llm_assessment_result.get('available'):
        llm_risk_level = llm_assessment_result.get('llm_risk_level', '')
        llm_risk_score = llm_assessment_result.get('llm_risk_score', 0)
        api_provider = llm_assessment_result.get('api_provider', 'unknown')
        
        print(f"LLM评估: 风险等级={llm_risk_level}, 评分={llm_risk_score}, API提供者={api_provider}")
        
        if llm_risk_level in ['较高风险', '极高风险'] and overall_risk_level in ['低风险', '较低风险']:
            overall_risk_level = '中等风险'
        
        llm_report = llm_assessment_result.get('assessment_report', '')
        if llm_report:
            explanation = f"{explanation}\n\n{llm_report}"
    
    response = {
        "risk_level": overall_risk_level,
        "risk_data": {
            "explanation": explanation,
            "coordinates": city_coordinates,
            "process": detailed_process,
            "factors": factors_with_weights,
            "risk_areas": risk_areas,
            "knowledge_graph": knowledge_graph_data,
            "workflow_result": workflow_result if _new_system_initialized and _workflow_controller else None,
            "mcp_tools_status": {name: "available" for name in _mcp_tools.keys()} if _mcp_tools else None,
            "lora_system_available": _lora_trainer is not None,
            "environmental_assessment": environmental_assessment,
            "sora_assessment": sora_assessment_result,
            "llm_assessment": llm_assessment_result,
            "gis_operators_available": True,
            "environmental_factors_available": True
        }
    }
    return response


class MyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def _convert_kg_for_network(self, kg_dict):
        """将知识图谱转换为前端网络可视化格式 — 显示全部节点和关系"""
        try:
            entities = []
            edges = []
            added_edges = set()
            
            # ========== 转换实体（保留完整属性） ==========
            for entity in kg_dict.get('entities', []):
                entity_id = entity.get('id', '')
                entity_type = entity.get('entity_type', '')
                name = entity.get('name', '')
                props = entity.get('properties', {})
                
                # 映射实体类型
                mapped_type = entity_type
                type_map = {
                    'airspace_region': 'city',
                    'risk_factor': 'risk_factor',
                    'infrastructure': 'infrastructure',
                    'sensitive_area': 'sensitive_area',
                    'weather_data': 'weather_data',
                    'subdistrict': 'subdistrict'
                }
                mapped_type = type_map.get(entity_type, entity_type)
                
                # 保留完整属性用于 tooltip 展示
                rich_props = dict(props)
                rich_props['entity_type'] = entity_type
                
                entities.append({
                    'id': entity_id,
                    'type': mapped_type,
                    'name': name,
                    'properties': rich_props,
                    # 原始类型用于区分
                    'entity_type': entity_type
                })
            
            # ========== 分类实体 ==========
            city_entities = [e for e in entities if e['type'] == 'city']
            infrastructure_entities = [e for e in entities if e['type'] == 'infrastructure']
            sensitive_entities = [e for e in entities if e['type'] == 'sensitive_area']
            risk_factor_entities = [e for e in entities if e['type'] == 'risk_factor']
            subdistrict_entities = [e for e in entities if e['type'] == 'subdistrict']
            weather_entities = [e for e in entities if e['type'] == 'weather_data']
            
            # ========== 处理已有关系 ==========
            kg_relations = kg_dict.get('relations', [])
            existing_edge_count = len(kg_relations)
            
            for relation in kg_relations:
                source_id = relation.get('source_id', '')
                target_id = relation.get('target_id', '')
                rel_type = relation.get('relation_type', '')
                
                edge_key = f"{source_id}->{target_id}:{rel_type}"
                if edge_key not in added_edges:
                    edges.append({
                        'source': source_id,
                        'target': target_id,
                        'type': rel_type
                    })
                    added_edges.add(edge_key)
            
            MAX_EDGES = 15000
            
            city_count = len(city_entities)
            infra_count = len(infrastructure_entities)
            sensitive_count = len(sensitive_entities)
            risk_count = len(risk_factor_entities)
            sub_count = len(subdistrict_entities)
            weather_count = len(weather_entities)
            
            for city in city_entities:
                sample_size = min(100, infra_count)
                for infra in infrastructure_entities[:sample_size]:
                    key = f"{city['id']}->{infra['id']}:CONTAINS"
                    if key not in added_edges and len(edges) < MAX_EDGES:
                        edges.append({'source': city['id'], 'target': infra['id'], 'type': 'CONTAINS'})
                        added_edges.add(key)
                
                sample_size = min(100, sensitive_count)
                for sensitive in sensitive_entities[:sample_size]:
                    key = f"{city['id']}->{sensitive['id']}:CONTAINS"
                    if key not in added_edges and len(edges) < MAX_EDGES:
                        edges.append({'source': city['id'], 'target': sensitive['id'], 'type': 'CONTAINS'})
                        added_edges.add(key)
                
                sample_size = min(50, sub_count)
                for sub in subdistrict_entities[:sample_size]:
                    key = f"{city['id']}->{sub['id']}:CONTAINS"
                    if key not in added_edges and len(edges) < MAX_EDGES:
                        edges.append({'source': city['id'], 'target': sub['id'], 'type': 'CONTAINS'})
                        added_edges.add(key)
                
                risk_sample = min(10, risk_count)
                for risk in risk_factor_entities[:risk_sample]:
                    key = f"{city['id']}->{risk['id']}:ASSOCIATED_WITH"
                    if key not in added_edges and len(edges) < MAX_EDGES:
                        edges.append({'source': city['id'], 'target': risk['id'], 'type': 'ASSOCIATED_WITH'})
                        added_edges.add(key)
                
                weather_sample = min(5, weather_count)
                for weather in weather_entities[:weather_sample]:
                    key = f"{city['id']}->{weather['id']}:ASSOCIATED_WITH"
                    if key not in added_edges and len(edges) < MAX_EDGES:
                        edges.append({'source': city['id'], 'target': weather['id'], 'type': 'ASSOCIATED_WITH'})
                        added_edges.add(key)
            
            infra_risk_limit = min(3, risk_count)
            for infra in infrastructure_entities[:50]:
                for risk in risk_factor_entities[:infra_risk_limit]:
                    if len(edges) >= MAX_EDGES:
                        break
                    key = f"{infra['id']}->{risk['id']}:INFLUENCES"
                    if key not in added_edges:
                        edges.append({'source': infra['id'], 'target': risk['id'], 'type': 'INFLUENCES'})
                        added_edges.add(key)
            
            sensitive_risk_limit = min(3, risk_count)
            for sensitive in sensitive_entities[:50]:
                for risk in risk_factor_entities[:sensitive_risk_limit]:
                    if len(edges) >= MAX_EDGES:
                        break
                    key = f"{sensitive['id']}->{risk['id']}:INFLUENCES"
                    if key not in added_edges:
                        edges.append({'source': sensitive['id'], 'target': risk['id'], 'type': 'INFLUENCES'})
                        added_edges.add(key)
            
            adjacency_limit = min(8, infra_count)
            for i in range(min(adjacency_limit, infra_count)):
                for j in range(i + 1, min(adjacency_limit + 1, infra_count)):
                    if len(edges) >= MAX_EDGES:
                        break
                    key = f"{infrastructure_entities[i]['id']}->{infrastructure_entities[j]['id']}:ADJACENT_TO"
                    if key not in added_edges:
                        edges.append({'source': infrastructure_entities[i]['id'], 'target': infrastructure_entities[j]['id'], 'type': 'ADJACENT_TO'})
                        added_edges.add(key)
            
            adjacency_limit = min(8, sensitive_count)
            for i in range(min(adjacency_limit, sensitive_count)):
                for j in range(i + 1, min(adjacency_limit + 1, sensitive_count)):
                    if len(edges) >= MAX_EDGES:
                        break
                    key = f"{sensitive_entities[i]['id']}->{sensitive_entities[j]['id']}:ADJACENT_TO"
                    if key not in added_edges:
                        edges.append({'source': sensitive_entities[i]['id'], 'target': sensitive_entities[j]['id'], 'type': 'ADJACENT_TO'})
                        added_edges.add(key)
            
            type_counts = {}
            for e in entities:
                t = e['type']
                type_counts[t] = type_counts.get(t, 0) + 1
            type_detail = ', '.join([f"{t}: {c}" for t, c in sorted(type_counts.items())])
            print(f"========== 知识图谱转换完成 ==========")
            print(f"  实体总数: {len(entities)}  ({type_detail})")
            print(f"  关系总数: {len(edges)} (原有 {existing_edge_count} 条, 补全 {len(edges) - existing_edge_count} 条)")
            print(f"  全部实体ID: {[e['id'] for e in entities]}")
            
            return {
                'entities': entities,
                'relations': edges
            }
        except Exception as e:
            print(f"转换知识图谱格式失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'entities': [],
                'relations': []
            }
    
    def _get_model_details(self, model_name):
        """获取模型详细信息"""
        try:
            model_path = os.path.join("./local_models", model_name)
            results_path = os.path.join(model_path, "training_results.json")
            
            if not os.path.exists(results_path):
                return {"success": False, "error": "模型结果文件不存在"}
            
            with open(results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            return {"success": True, "details": results}
        except Exception as e:
            print(f"获取模型详情出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _get_training_data_preview(self, model_name):
        """获取训练数据预览"""
        try:
            model_path = os.path.join("./local_models", model_name)
            preview_path = os.path.join(model_path, "training_data_preview.json")
            
            if not os.path.exists(preview_path):
                return {"success": False, "error": "训练数据预览文件不存在"}
            
            with open(preview_path, 'r', encoding='utf-8') as f:
                preview = json.load(f)
            
            return {"success": True, "preview": preview}
        except Exception as e:
            print(f"获取训练数据预览出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def do_POST(self):
        response_data = None
        status_code = 200
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''
            
            if self.path == '/evaluate':
                print(f"收到POST请求: {self.path}")
                user_input = '未知地区'
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        user_input = request_data.get('region', '未知地区')
                        print(f"接收到的用户输入: {user_input}")
                except Exception as e:
                    print(f"解析请求数据出错: {str(e)}")
                
                # 使用完整本地模型推理器提取位置关键词（使用本地微调好的模型）
                print("正在使用完整本地LoRA微调模型提取位置关键词...")
                complete_inference = get_complete_inference()
                
                # 提取位置
                extraction_result = complete_inference.extract_location(user_input)
                print(f"提取结果: {extraction_result}")
                
                region = extraction_result['primary_location']
                print(f"最终使用的区域: {region}")
                
                # 进行评估
                response_data = evaluate_region(region, extraction_result)
                
                # 更新最后评估的区域
                global _last_assessed_region
                _last_assessed_region = region
                
                # 保存评估结果到PostGIS数据库（如果可用）
                try:
                    if _postgis_db:
                        print("[PostGIS] 正在保存评估结果到数据库...")
                        # 计算总体风险评分
                        risk_level_map = {
                            "低风险": 0,
                            "较低风险": 1,
                            "中等风险": 2,
                            "较高风险": 3,
                            "极高风险": 4
                        }
                        overall_risk_level = response_data.get('risk_level', '中等风险')
                        risk_score = risk_level_map.get(overall_risk_level, 2)
                        
                        # 保存评估历史记录
                        assessment_id = _postgis_db.add_assessment_history(
                            region=region,
                            risk_level=overall_risk_level,
                            risk_score=risk_score,
                            risk_data=response_data.get('risk_data', {}),
                            user_input=user_input
                        )
                        
                        if assessment_id:
                            print(f"[PostGIS] 评估历史记录已保存，ID: {assessment_id}")
                            
                            # 保存风险区域
                            risk_areas = response_data.get('risk_data', {}).get('risk_areas', [])
                            for area in risk_areas:
                                area_id = _postgis_db.add_risk_area(
                                    assessment_id=assessment_id,
                                    name=area.get('name', '未知区域'),
                                    level=area.get('level', '中等风险'),
                                    coordinates=area.get('coordinates'),
                                    explanation=area.get('explanation'),
                                    key_factors=area.get('key_factors')
                                )
                                if area_id:
                                    print(f"[PostGIS] 风险区域已保存: {area.get('name')}")
                        else:
                            print("[PostGIS] 评估历史记录保存失败")
                except Exception as db_error:
                    print(f"[PostGIS] 保存评估结果出错: {db_error}")
                    import traceback
                    traceback.print_exc()
                
                # 在响应中添加提取过程信息
                response_data['input_processing'] = extraction_result
            
            elif self.path == '/enhanced/kg_tree':
                print(f"收到知识图谱树状图请求: {self.path}")
                region = _last_assessed_region
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        region = request_data.get('region', region)
                except Exception as e:
                    print(f"解析请求数据出错: {str(e)}")
                
                print(f"为区域'{region}'生成知识图谱")
                try:
                    from knowledge_graph.dynamic_builder import get_dynamic_builder
                    builder = get_dynamic_builder()
                    kg_data = builder.build_for_city(region) if hasattr(builder, 'build_for_city') else None
                    if kg_data:
                        response_data = {
                            "success": True,
                            "region": region,
                            "knowledge_graph": kg_data,
                            "source": "dynamic_builder"
                        }
                    else:
                        response_data = {
                            "success": False,
                            "region": region,
                            "message": "无法构建知识图谱"
                        }
                except Exception as e:
                    print(f"构建知识图谱失败: {e}")
                    response_data = {
                        "success": False,
                        "region": region,
                        "message": f"构建失败: {str(e)}"
                    }
            
            elif self.path == '/enhanced/iteration/start':
                print(f"收到启动迭代训练请求: {self.path}")
                num_iterations = 3
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        num_iterations = request_data.get('num_iterations', 3)
                except Exception as e:
                    print(f"解析请求数据出错: {str(e)}")
                
                response_data = {
                    "success": True,
                    "message": f"迭代训练已启动，循环{num_iterations}轮",
                    "note": "使用LoRA训练器和数据生成器"
                }
            
            elif self.path == '/enhanced/iteration/stop':
                print(f"收到停止迭代训练请求: {self.path}")
                response_data = {"success": True, "message": "迭代训练已停止"}
            
            elif self.path == '/enhanced/iteration/status':
                print(f"收到迭代训练状态请求: {self.path}")
                response_data = get_new_system_status()
            
            elif self.path == '/enhanced/dynamic_route':
                print(f"收到动态评估路线请求: {self.path}")
                region = '武汉'
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        region = request_data.get('region', '武汉')
                except Exception as e:
                    print(f"解析请求数据出错: {str(e)}")
                
                try:
                    from knowledge_graph.dynamic_builder import get_dynamic_builder
                    builder = get_dynamic_builder()
                    kg_data = builder.build_for_city(region) if hasattr(builder, 'build_for_city') else None
                    response_data = {
                        "success": True,
                        "region": region,
                        "knowledge_graph": kg_data,
                        "route": f"{region}动态评估路线已生成",
                        "source": "dynamic_builder"
                    }
                except Exception as e:
                    print(f"动态路线生成失败: {e}")
                    response_data = {
                        "success": False,
                        "region": region,
                        "message": f"路线生成失败: {str(e)}"
                    }
            
            elif self.path == '/enhanced/assessment/history':
                print(f"收到评估历史请求: {self.path}")
                region = None
                limit = 50
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        region = request_data.get('region')
                        limit = request_data.get('limit', 50)
                except Exception as e:
                    print(f"解析请求数据出错: {str(e)}")
                
                try:
                    if _postgis_db:
                        print("[PostGIS] 从PostGIS获取评估历史")
                        history = _postgis_db.get_assessment_history(region, limit)
                        response_data = {
                            "success": True,
                            "source": "postgis",
                            "history": history
                        }
                    else:
                        response_data = {
                            "success": True,
                            "source": "local",
                            "history": [],
                            "note": "PostGIS不可用，无本地历史记录"
                        }
                except Exception as e:
                    print(f"[PostGIS] 获取历史记录失败: {e}")
                    response_data = {
                        "success": True,
                        "source": "local",
                        "history": [],
                        "note": f"获取失败: {str(e)}"
                    }
            
            elif self.path == '/postgis/assessment/detail':
                print(f"收到评估详情请求: {self.path}")
                assessment_id = None
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        assessment_id = request_data.get('assessment_id')
                except Exception as e:
                    print(f"解析请求数据出错: {str(e)}")
                
                if assessment_id is not None and _postgis_db:
                    try:
                        detail = _postgis_db.get_assessment_with_risk_areas(assessment_id)
                        if detail:
                            response_data = {"success": True, "detail": detail}
                        else:
                            response_data = {"success": False, "error": "未找到评估记录"}
                    except Exception as e:
                        print(f"[PostGIS] 获取评估详情失败: {e}")
                        response_data = {"success": False, "error": str(e)}
                else:
                    response_data = {"success": False, "error": "PostGIS数据库不可用或缺少assessment_id"}
            
            elif self.path == '/postgis/stats':
                print(f"收到PostGIS统计请求: {self.path}")
                if _postgis_db:
                    try:
                        with _postgis_db.conn.cursor() as cur:
                            cur.execute("SELECT COUNT(*) FROM cities;")
                            cities_count = cur.fetchone()[0]
                            
                            cur.execute("SELECT COUNT(*) FROM infrastructure;")
                            infra_count = cur.fetchone()[0]
                            
                            cur.execute("SELECT COUNT(*) FROM sensitive_areas;")
                            sensitive_count = cur.fetchone()[0]
                            
                            cur.execute("SELECT COUNT(*) FROM assessment_history;")
                            assessment_count = cur.fetchone()[0]
                            
                            cur.execute("SELECT COUNT(*) FROM risk_areas;")
                            risk_areas_count = cur.fetchone()[0]
                            
                            cur.execute("SELECT COUNT(*) FROM knowledge_graphs;")
                            kg_count = cur.fetchone()[0]
                        
                        response_data = {
                            "success": True,
                            "stats": {
                                "cities": cities_count,
                                "infrastructure": infra_count,
                                "sensitive_areas": sensitive_count,
                                "assessments": assessment_count,
                                "risk_areas": risk_areas_count,
                                "knowledge_graphs": kg_count
                            }
                        }
                    except Exception as e:
                        print(f"[PostGIS] 获取统计数据失败: {e}")
                        response_data = {"success": False, "error": str(e)}
                else:
                    response_data = {"success": False, "error": "PostGIS数据库不可用"}
            
            elif self.path == '/weather':
                print(f"收到POST请求: {self.path}")
                city_name = '未知城市'
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        input_text = request_data.get('city', '')
                        print(f"原始输入: {input_text}")
                        
                        inference = get_complete_inference()
                        extracted = inference.extract_location(input_text)
                        city_name = extracted.get('primary_location', '未知城市')
                        print(f"提取到的城市: {city_name}")
                except Exception as e:
                    print(f"解析请求数据出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                weather_data = get_weather_data(city_name)
                print(f"天气数据: {weather_data}")
                if weather_data.get('source') == '备用数据':
                    response_data = {
                        "success": False,
                        "error": "无法获取天气数据，请检查城市名称是否正确"
                    }
                else:
                    response_data = {
                        "success": True,
                        "weather": weather_data
                    }
            
            elif self.path == '/train/generate_dataset':
                print(f"收到生成数据集请求: {self.path}")
                try:
                    builder = RealDatasetBuilder()
                    dataset = builder.generate_risk_assessment_dataset()
                    filepath = builder.save_dataset(dataset)
                    
                    risk_distribution = {}
                    city_count = 0
                    for item in dataset:
                        if item.get("type") == "risk_assessment":
                            level = item.get("risk_level", "未知")
                            risk_distribution[level] = risk_distribution.get(level, 0) + 1
                            city_count += 1
                    
                    response_data = {
                        "success": True,
                        "filepath": filepath,
                        "total_samples": len(dataset),
                        "city_count": city_count,
                        "risk_distribution": risk_distribution
                    }
                except Exception as e:
                    print(f"生成数据集出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/train/lora':
                print(f"收到LoRA训练请求: {self.path}")
                result = {"success": False, "error": "未知操作"}
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        action = request_data.get('action', 'status')
                        
                        if action == 'generate_data':
                            if _training_data_generator:
                                sample_case = _training_data_generator.generate_risk_assessment_case(
                                    region=request_data.get('region', '测试区域'),
                                    risk_level=request_data.get('risk_level', '中等风险'),
                                    factors=request_data.get('factors', []),
                                    explanation=request_data.get('explanation', '测试说明')
                                )
                                result = {"success": True, "data": sample_case}
                            else:
                                result = {"success": False, "error": "训练数据生成器未初始化"}
                        
                        elif action == 'start_training':
                            if _lora_trainer:
                                from training.simple_data_generator import SimpleTrainingDataGenerator
                                generator = SimpleTrainingDataGenerator(db_path="./data/risk_assessment.db")
                                
                                print("正在生成训练数据...")
                                training_data = generator.generate_training_data(num_samples=50)
                                print(f"训练数据已生成: {len(training_data)} 条")
                                
                                model_path = _lora_trainer.start_training(training_data)
                                result = {"success": True, "model_path": model_path}
                            else:
                                result = {"success": False, "error": "LoRA训练器未初始化"}
                        
                        elif action == 'list_models':
                            if _lora_trainer:
                                try:
                                    models = _lora_trainer.list_trained_models()
                                    result = {"success": True, "models": models}
                                except AttributeError:
                                    result = {"success": True, "models": [], "note": "trainer不支持list_trained_models"}
                            else:
                                result = {"success": False, "error": "LoRA训练器未初始化"}
                        
                        elif action == 'get_model_details':
                            model_name = request_data.get('model_name', '')
                            if model_name:
                                result = self._get_model_details(model_name)
                            else:
                                result = {"success": False, "error": "未提供模型名称"}
                        
                        elif action == 'get_training_data_preview':
                            model_name = request_data.get('model_name', '')
                            if model_name:
                                result = self._get_training_data_preview(model_name)
                            else:
                                result = {"success": False, "error": "未提供模型名称"}
                        
                        else:
                            result = {"success": False, "error": f"未知操作: {action}"}
                except Exception as e:
                    print(f"处理LoRA训练请求出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    result = {"success": False, "error": str(e)}
                
                response_data = result
            
            elif self.path == '/training/real_data':
                print(f"收到训练数据请求: {self.path}")
                result = {"success": False, "error": "未知操作"}
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        action = request_data.get('action', 'status')
                        
                        from training.simple_data_generator import SimpleTrainingDataGenerator
                        data_gen = SimpleTrainingDataGenerator(db_path="./data/risk_assessment.db")
                        
                        if action == 'generate_single_case':
                            city_name = request_data.get('city_name', '武汉')
                            city_data = CHINA_CITY_DATA.get(city_name, {})
                            case = data_gen.generate_risk_assessment_case(
                                region=city_name,
                                risk_level=request_data.get('risk_level', '中等风险'),
                                factors=request_data.get('factors', ['人口密度', '建筑物密度']),
                                explanation=f"{city_name}低空风险评估案例"
                            )
                            if case:
                                case['city_data'] = city_data
                                result = {"success": True, "data": case}
                            else:
                                result = {"success": False, "error": "生成案例失败"}
                        
                        elif action == 'generate_batch':
                            num_cities = request_data.get('num_cities', 5)
                            cases = []
                            cities = list(CHINA_CITY_DATA.keys())[:num_cities]
                            for city in cities:
                                city_data = CHINA_CITY_DATA.get(city, {})
                                case = data_gen.generate_risk_assessment_case(
                                    region=city,
                                    risk_level='中等风险',
                                    factors=['人口密度', '建筑物密度'],
                                    explanation=f"{city}低空风险评估"
                                )
                                if case:
                                    case['city_data'] = city_data
                                    cases.append(case)
                            result = {"success": True, "data": cases, "count": len(cases)}
                        
                        elif action == 'get_city_data':
                            city_name = request_data.get('city_name')
                            if city_name:
                                city_data = CHINA_CITY_DATA.get(city_name)
                                if city_data:
                                    result = {"success": True, "data": city_data}
                                else:
                                    result = {"success": False, "error": "获取城市数据失败"}
                            else:
                                result = {"success": False, "error": "未提供城市名称"}
                        
                        else:
                            result = {"success": False, "error": f"未知操作: {action}"}
                except Exception as e:
                    print(f"处理训练数据请求出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    result = {"success": False, "error": str(e)}
                
                response_data = result
            
            elif self.path == '/database/stats':
                print(f"收到数据库统计请求: {self.path}")
                try:
                    from mcp_tools import get_database_tool
                    db = get_database_tool()
                    stats = db.get_statistics()
                    response_data = {"success": True, "stats": stats}
                except Exception as e:
                    print(f"获取数据库统计出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/monitoring/metrics':
                print(f"收到监控指标请求: {self.path}")
                try:
                    from mcp_tools import get_monitoring_tool
                    monitor = get_monitoring_tool()
                    metrics = monitor.collect_metrics()
                    response_data = {"success": True, "metrics": metrics}
                except Exception as e:
                    print(f"获取监控指标出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/knowledge_graph/visualize':
                print(f"收到知识图谱可视化请求: {self.path}")
                region = _last_assessed_region
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        region = request_data.get('region', region)
                except Exception as e:
                    print(f"解析请求数据出错: {str(e)}")
                
                try:
                    if _knowledge_base:
                        print(f"为区域'{region}'生成知识图谱可视化")
                        city_kg_dict = _knowledge_base.load_kg(region)
                        
                        if not city_kg_dict:
                            print(f"知识库中无'{region}'的知识图谱，构建新的")
                            dynamic_builder = get_dynamic_builder()
                            city_kg = dynamic_builder.build_for_city(region, use_llm=False)
                            city_kg_dict = city_kg.to_dict()
                            _knowledge_base.save_kg(region, city_kg_dict)
                        
                        # 转换为前端期望的格式
                        network_kg = self._convert_kg_for_network(city_kg_dict)
                        
                        response_data = {
                            "success": True,
                            "knowledge_graph": network_kg
                        }
                    else:
                        response_data = {"success": False, "error": "知识库未初始化"}
                except Exception as e:
                    print(f"生成知识图谱可视化出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/knowledge_base/stats':
                print(f"收到知识库统计请求: {self.path}")
                try:
                    if _knowledge_base:
                        stats = _knowledge_base.get_kb_statistics()
                        response_data = {"success": True, "stats": stats}
                    else:
                        response_data = {"success": False, "error": "知识库未初始化"}
                except Exception as e:
                    print(f"获取知识库统计出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/graph_rag/retrieve':
                print(f"收到 GraphRAG 检索请求: {self.path}")
                city_name = _last_assessed_region
                query = ""
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        city_name = request_data.get('city_name', city_name)
                        query = request_data.get('query', '')
                except Exception:
                    pass
                
                try:
                    if _graph_rag and _graph_rag.available:
                        result = _graph_rag.retrieve_for_risk_assessment(city_name, query)
                        response_data = {"success": True, "result": result}
                    else:
                        response_data = {
                            "success": False,
                            "error": "GraphRAG 不可用，请确保内存图存储已加载"
                        }
                except Exception as e:
                    print(f"GraphRAG 检索出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/graph_rag/context':
                print(f"收到 GraphRAG 上下文请求: {self.path}")
                city_name = _last_assessed_region
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        city_name = request_data.get('city_name', city_name)
                except Exception:
                    pass
                
                try:
                    if _knowledge_base:
                        rag_context = _knowledge_base.get_rag_context(city_name)
                        if rag_context:
                            response_data = {"success": True, "context": rag_context}
                        else:
                            response_data = {
                                "success": False,
                                "error": "GraphRAG 上下文不可用",
                                "context": {
                                    'city_name': city_name,
                                    'entity_count': 0,
                                    'relation_count': 0,
                                    'risk_factor_count': 0
                                }
                            }
                    else:
                        response_data = {"success": False, "error": "知识库未初始化"}
                except Exception as e:
                    print(f"获取 GraphRAG 上下文出错: {str(e)}")
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/graph_rag/search':
                print(f"收到 GraphRAG 搜索请求: {self.path}")
                query_text = ""
                city_name = None
                limit = 10
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        query_text = request_data.get('query', '')
                        city_name = request_data.get('city_name')
                        limit = request_data.get('limit', 10)
                except Exception:
                    pass
                
                try:
                    if _graph_rag:
                        entities = _graph_rag.search_entities(query_text, city_name, limit)
                        response_data = {"success": True, "entities": entities}
                    else:
                        response_data = {"success": False, "error": "GraphRAG 未初始化"}
                except Exception as e:
                    print(f"GraphRAG 搜索出错: {str(e)}")
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/graph_rag/prompt':
                print(f"收到 GraphRAG Prompt 请求: {self.path}")
                city_name = _last_assessed_region
                user_query = ""
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        city_name = request_data.get('city_name', city_name)
                        user_query = request_data.get('query', '请进行风险评估')
                except Exception:
                    pass
                
                try:
                    if _graph_rag and _graph_rag.available:
                        prompt, retrieval = _graph_rag.retrieve_and_prompt(city_name, user_query)
                        response_data = {
                            "success": True,
                            "prompt": prompt,
                            "retrieval_summary": {
                                "entity_count": retrieval['graph_statistics'].get('total_entities', 0),
                                "relation_count": retrieval['graph_statistics'].get('total_relations', 0),
                                "risk_factors": len(retrieval['risk_factors']),
                                "infrastructure": len(retrieval['infrastructure']),
                                "sensitive_areas": len(retrieval['sensitive_areas'])
                            }
                        }
                    else:
                        response_data = {"success": False, "error": "GraphRAG 不可用"}
                except Exception as e:
                    print(f"GraphRAG Prompt 构建出错: {str(e)}")
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/graph_rag/generate':
                print(f"收到 GraphRAG 增强生成请求: {self.path}")
                city_name = _last_assessed_region
                user_query = "请进行风险评估"
                use_llm = True
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        city_name = request_data.get('city_name', city_name)
                        user_query = request_data.get('query', user_query)
                        use_llm = request_data.get('use_llm', use_llm)
                except Exception:
                    pass
                
                try:
                    if _knowledge_base:
                        result = _knowledge_base.generate_with_llm(city_name, user_query)
                        response_data = {
                            "success": True,
                            "city_name": city_name,
                            "query": user_query,
                            "response": result.get('response', ''),
                            "used_llm": result.get('used_llm', False),
                            "retrieval_summary": {
                                "entity_count": result.get('retrieval', {}).get('graph_statistics', {}).get('total_entities', 0),
                                "relation_count": result.get('retrieval', {}).get('graph_statistics', {}).get('total_relations', 0)
                            }
                        }
                    else:
                        response_data = {"success": False, "error": "知识库未初始化"}
                except Exception as e:
                    print(f"GraphRAG 增强生成出错: {str(e)}")
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/case_kg/stats':
                print(f"收到案例知识图谱统计请求: {self.path}")
                try:
                    if _case_kg_builder:
                        stats = _case_kg_builder.get_case_statistics()
                        response_data = {"success": True, "statistics": stats}
                    else:
                        response_data = {"success": False, "error": "案例构建器未初始化"}
                except Exception as e:
                    print(f"案例统计出错: {str(e)}")
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/case_kg/build':
                print(f"收到案例知识图谱构建请求: {self.path}")
                try:
                    if _knowledge_base:
                        case_count = _knowledge_base.build_case_kg()
                        response_data = {
                            "success": True,
                            "cases_loaded": case_count,
                            "message": f"已从 {case_count} 条案例构建知识图谱"
                        }
                    else:
                        response_data = {"success": False, "error": "知识库未初始化"}
                except Exception as e:
                    print(f"案例图谱构建出错: {str(e)}")
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/case_kg/cities':
                print(f"收到案例城市列表请求: {self.path}")
                try:
                    if _case_kg_builder:
                        cases = _case_kg_builder.get_cases()
                        cities = list(set(c.get('city', '') for c in cases if c.get('city')))
                        response_data = {"success": True, "cities": sorted(cities), "total_cases": len(cases)}
                    else:
                        response_data = {"success": False, "error": "案例构建器未初始化"}
                except Exception as e:
                    print(f"案例城市列表出错: {str(e)}")
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/spatial_risk/init':
                print(f"收到空间风险模块初始化请求: {self.path}")
                try:
                    city_name = '武汉'
                    city_center = (114.3055, 30.5931)
                    try:
                        if post_data:
                            request_data = json.loads(post_data.decode('utf-8'))
                            city_name = request_data.get('city_name', city_name)
                            city_center = request_data.get('city_center', city_center)
                    except Exception as e:
                        print(f"解析请求数据出错: {str(e)}")
                    
                    if _spatial_risk_integration:
                        success = _spatial_risk_integration.initialize(city_name, city_center)
                        if success:
                            entities = _spatial_risk_integration.get_spatial_entities()
                            response_data = {
                                "success": True,
                                "message": "空间风险模块初始化成功",
                                "spatial_entities": entities
                            }
                        else:
                            response_data = {"success": False, "error": "空间风险模块初始化失败"}
                    else:
                        response_data = {"success": False, "error": "空间风险集成模块未初始化"}
                except Exception as e:
                    print(f"空间风险模块初始化出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/spatial_risk/assess':
                print(f"收到空间风险评估请求: {self.path}")
                try:
                    flight_plan_data = {
                        "waypoints": [[30.5931, 114.3055], [30.6, 114.31], [30.61, 114.32]],
                        "altitude": 100,
                        "speed": 50
                    }
                    city_name = _last_assessed_region
                    sora_ground_data = None
                    sora_air_data = None
                    sora_natural_data = None
                    sora_topology_data = None
                    try:
                        if post_data:
                            request_data = json.loads(post_data.decode('utf-8'))
                            flight_plan_data = request_data.get('flight_plan', flight_plan_data)
                            city_name = request_data.get('city_name', city_name)
                            sora_ground_data = request_data.get('sora_ground_data')
                            sora_air_data = request_data.get('sora_air_data')
                            sora_natural_data = request_data.get('sora_natural_data')
                            sora_topology_data = request_data.get('sora_topology_data')
                    except Exception as e:
                        print(f"解析请求数据出错: {str(e)}")
                    
                    if _spatial_risk_integration:
                        assessment_result = _spatial_risk_integration.assess_risk(
                            flight_plan_data, city_name,
                            sora_ground_data, sora_air_data,
                            sora_natural_data, sora_topology_data
                        )
                        response_data = assessment_result
                    else:
                        response_data = {"success": False, "error": "空间风险集成模块未初始化"}
                except Exception as e:
                    print(f"空间风险评估出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/spatial_risk/kg':
                print(f"收到空间风险知识图谱请求: {self.path}")
                try:
                    if _spatial_risk_integration:
                        kg_data = _spatial_risk_integration.get_knowledge_graph_data()
                        response_data = {
                            "success": True,
                            "knowledge_graph": kg_data
                        }
                    else:
                        response_data = {"success": False, "error": "空间风险集成模块未初始化"}
                except Exception as e:
                    print(f"获取空间风险知识图谱出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/spatial_risk/entities':
                print(f"收到空间实体列表请求: {self.path}")
                try:
                    if _spatial_risk_integration:
                        entities = _spatial_risk_integration.get_spatial_entities()
                        response_data = {
                            "success": True,
                            "spatial_entities": entities
                        }
                    else:
                        response_data = {"success": False, "error": "空间风险集成模块未初始化"}
                except Exception as e:
                    print(f"获取空间实体列表出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}
            
            elif self.path == '/ahp/matrix/set':
                try:
                    body = json.loads(post_data.decode('utf-8'))
                    matrix = body.get('matrix')
                    if not matrix or not isinstance(matrix, list):
                        response_data = {"ok": False, "error": "请提供有效的判断矩阵(matrix字段，二维数组)"}
                    else:
                        from mcp_tools.ahp_weight_calculator import get_ahp_calculator
                        calc = get_ahp_calculator()
                        response_data = calc.set_judgment_matrix(matrix)
                except Exception as e:
                    response_data = {"ok": False, "error": str(e)}

            elif self.path == '/ahp/cell/set':
                try:
                    body = json.loads(post_data.decode('utf-8'))
                    row = body.get('row')
                    col = body.get('col')
                    value = body.get('value')
                    if row is None or col is None or value is None:
                        response_data = {"ok": False, "error": "请提供row、col、value三个参数"}
                    else:
                        from mcp_tools.ahp_weight_calculator import get_ahp_calculator
                        calc = get_ahp_calculator()
                        response_data = calc.set_cell(int(row), int(col), float(value))
                except Exception as e:
                    response_data = {"ok": False, "error": str(e)}

            elif self.path == '/ahp/reset':
                from mcp_tools.ahp_weight_calculator import get_ahp_calculator
                calc = get_ahp_calculator()
                response_data = calc.reset_to_default()

            elif self.path == '/ahp/suggest':
                try:
                    body = json.loads(post_data.decode('utf-8'))
                    feedback = body.get('feedback', '')
                    city_data = body.get('city_data')
                    from mcp_tools.ahp_weight_calculator import get_ahp_calculator
                    calc = get_ahp_calculator()

                    def llm_callback(current_matrix, city_characteristics, feedback):
                        try:
                            from knowledge_graph.local_llm_client import get_local_llm
                            llm = get_local_llm()
                            if not llm.available:
                                return ""
                            prompt = f"""作为AHP层次分析法专家，请分析以下低空空域风险评估判断矩阵并提出优化建议。

当前判断矩阵（5因素-人口密度/空中交通/建筑物密度/天气条件/地理拓扑）：
{json.dumps(current_matrix['matrix'], ensure_ascii=False)}
当前权重：{json.dumps(current_matrix['weights'], ensure_ascii=False)}
CR一致性比率：{current_matrix['cr']}

用户反馈：{feedback}
城市特征：{json.dumps(city_characteristics or {}, ensure_ascii=False)}

请提供具体的判断矩阵调整建议，用中文简洁回答。"""
                            result = llm.chat(
                                [{'role': 'user', 'content': prompt}],
                                temperature=0.3, max_tokens=800
                            )
                            if result and 'choices' in result:
                                return result['choices'][0]['message']['content'].strip()
                            return ""
                        except Exception as e:
                            return f"LLM建议生成失败: {e}"

                    calc.set_llm_callback(llm_callback)
                    suggestions = calc.suggest_matrix_adjustment(
                        feedback=feedback,
                        city_characteristics=city_data
                    )
                    calc.set_llm_callback(None)
                    response_data = {"ok": True, **suggestions}
                except Exception as e:
                    response_data = {"ok": False, "error": str(e)}

            elif self.path == '/evaluate/bleu':
                print(f"收到BLEU评估请求: {self.path}")
                action = "run"
                try:
                    if post_data:
                        request_data = json.loads(post_data.decode('utf-8'))
                        action = request_data.get('action', 'run')
                except Exception as e:
                    print(f"解析BLEU请求数据出错: {str(e)}")

                try:
                    evaluator = BLEUEvaluator()

                    if action == "info":
                        ref_reports = evaluator.get_reference_reports()
                        cases_info = [
                            {
                                "case_id": r["id"],
                                "scenario": r["scenario"],
                                "risk_level": r["risk_level"],
                                "sail_level": r["sail_level"],
                                "user_query": r["user_query"],
                                "reference_length": len(r["reference_report"])
                            }
                            for r in ref_reports
                        ]
                        response_data = {
                            "success": True,
                            "action": "info",
                            "num_cases": len(ref_reports),
                            "cases": cases_info
                        }
                    else:
                        print("正在运行BLEU评估...")
                        result = evaluate_bleu_from_cases()
                        output_path = evaluator.save_report(result)
                        response_data = {
                            "success": True,
                            "action": "run",
                            "report_path": output_path,
                            "result": result
                        }
                except Exception as e:
                    print(f"BLEU评估出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    response_data = {"success": False, "error": str(e)}

            else:
                status_code = 404
                response_data = {"error": "未找到"}
            
        except Exception as e:
            print(f"处理POST请求出错: {str(e)}")
            import traceback
            traceback.print_exc()
            status_code = 500
            response_data = {"error": str(e)}
        
        try:
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            if response_data:
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            print(f"发送响应出错: {str(e)}")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/system/status':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                status = get_new_system_status()
                self.wfile.write(json.dumps(status, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                print(f"获取系统状态出错: {str(e)}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Internal server error: {str(e)}".encode('utf-8'))
        elif self.path == '/health':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "healthy"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                print(f"处理健康检查请求出错: {str(e)}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Internal server error: {str(e)}".encode('utf-8'))
        elif self.path == '/':
            try:
                with open('interface.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                print(f"读取interface.html文件出错: {str(e)}")
                self.send_response(404)
                self.end_headers()
                self.wfile.write(f"File not found: {str(e)}".encode('utf-8'))
        elif self.path == '/script.js':
            try:
                with open('script.js', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'application/javascript')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                print(f"读取script.js文件出错: {str(e)}")
                self.send_response(404)
                self.end_headers()
                self.wfile.write(f"File not found: {str(e)}".encode('utf-8'))
        elif self.path == '/styles.css':
            try:
                with open('styles.css', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/css')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                print(f"读取styles.css文件出错: {str(e)}")
                self.send_response(404)
                self.end_headers()
                self.wfile.write(f"File not found: {str(e)}".encode('utf-8'))
        elif self.path == '/ahp/matrix':
            try:
                from mcp_tools.ahp_weight_calculator import get_ahp_calculator
                calc = get_ahp_calculator()
                response = json.dumps(calc.get_matrix_with_labels(), ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif self.path == '/ahp/config':
            try:
                from mcp_tools.ahp_weight_calculator import get_ahp_calculator
                calc = get_ahp_calculator()
                response = json.dumps(calc.export_config(), ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()


print("=" * 80)
print("低空空域风险评估系统")
print("=" * 80)

init_new_system()

print("=" * 80)
print("Starting HTTP server...")
print("=" * 80)
print(f"PORT: {PORT}")
print(f"AMAP_KEY: {AMAP_KEY[:10]}...")
print("=" * 80)

try:
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("0.0.0.0", PORT), MyHTTPRequestHandler)
    print(f"Server running at http://127.0.0.1:{PORT}")
    
    httpd.serve_forever()
    
except KeyboardInterrupt:
    print("\nServer is shutting down...")
    if 'httpd' in locals():
        httpd.shutdown()
except Exception as e:
    print(f"Error starting server: {e}")
    import traceback
    traceback.print_exc()

print("Server stopped.")
