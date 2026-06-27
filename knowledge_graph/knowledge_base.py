"""
知识图谱知识库存储模块 — PostGIS + 内存图 + JSON 回退
存储策略: PostGIS 优先 → 内存图同步 → JSON 文件回退
集成 GraphRAG 检索引擎和本地大模型
"""

import sys
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.visualizer import (
    create_general_low_altitude_kg,
    get_kg_visualizer
)
from knowledge_graph.dynamic_builder import get_dynamic_builder


class KnowledgeBase:
    """知识图谱知识库（PostGIS + 内存图 + JSON 回退）"""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'data', 'knowledge_base'
            )

        self.base_dir = base_dir
        self.ensure_storage_dir()

        self._postgis_db: Any = None
        self._graph_store: Any = None
        self._graph_rag: Any = None
        self._llm: Any = None

        self._kg_cache: Dict[str, Dict[str, Any]] = {}

        self._general_kg = None
        self._load_general_kg()

    def set_postgis_db(self, db):
        """设置 PostGIS 数据库连接"""
        self._postgis_db = db
        print(f"[KnowledgeBase] 已关联 PostGIS 数据库")

    def set_graph_store(self, store):
        """设置内存图存储引擎"""
        self._graph_store = store
        print("[KnowledgeBase] 已关联内存图存储引擎")

    def set_graph_rag(self, graph_rag):
        """设置 GraphRAG 引擎"""
        self._graph_rag = graph_rag
        print("[KnowledgeBase] 已关联 GraphRAG 检索引擎")

    def set_llm(self, llm):
        """设置本地大模型客户端"""
        self._llm = llm
        print("[KnowledgeBase] 已关联本地大模型")

    @property
    def postgis_available(self) -> bool:
        return self._postgis_db is not None

    @property
    def graph_store_available(self) -> bool:
        return self._graph_store is not None and self._graph_store.available

    @property
    def graph_rag_available(self) -> bool:
        return self._graph_rag is not None and self._graph_rag.available

    @property
    def llm_available(self) -> bool:
        return self._llm is not None and self._llm.available

    def ensure_storage_dir(self):
        """确保存储目录存在"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'images'), exist_ok=True)

    def _load_general_kg(self):
        """加载通用知识图谱"""
        general_kg_path = os.path.join(self.base_dir, 'general_low_altitude_kg.json')

        if os.path.exists(general_kg_path):
            try:
                with open(general_kg_path, 'r', encoding='utf-8') as f:
                    self._general_kg = json.load(f)
                print("[KnowledgeBase] 已加载通用低空空域知识图谱")
            except Exception as e:
                print(f"[KnowledgeBase] 加载通用知识图谱失败: {e}")
                self._general_kg = create_general_low_altitude_kg()
        else:
            self._general_kg = create_general_low_altitude_kg()
            self.save_kg('general_low_altitude', self._general_kg)
            print("[KnowledgeBase] 已创建并保存通用低空空域知识图谱")

    def get_general_kg(self) -> Dict[str, Any]:
        """获取通用知识图谱"""
        return self._general_kg

    def save_kg(
        self,
        city_name: str,
        kg_data: Dict[str, Any],
        region_name: Optional[str] = None
    ) -> bool:
        """
        保存城市知识图谱

        策略：PostGIS 优先 → 内存图同步 → 文件回退
        """
        try:
            cache_key = f"{city_name}:{region_name}" if region_name else city_name
            self._kg_cache[cache_key] = kg_data

            postgis_saved = False

            if self.postgis_available and city_name != 'general_low_altitude':
                try:
                    entities = kg_data.get('entities', [])
                    relations = kg_data.get('relations', [])
                    metadata = {
                        'region_name': region_name,
                        'created_at': datetime.now().isoformat()
                    }

                    self._postgis_db.save_knowledge_graph(
                        city_name=city_name,
                        region_name=region_name,
                        entities=entities,
                        relations=relations,
                        metadata=metadata
                    )
                    postgis_saved = True
                    print(f"[KnowledgeBase] 知识图谱已保存到 PostGIS: {city_name}")
                except Exception as pg_error:
                    print(f"[KnowledgeBase] 保存到 PostGIS 失败: {pg_error}")

            if self.graph_store_available and city_name != 'general_low_altitude':
                try:
                    entities = kg_data.get('entities', [])
                    relations = kg_data.get('relations', [])
                    self._graph_store.save_knowledge_graph(
                        city_name=city_name,
                        entities=entities,
                        relations=relations,
                        metadata={'region_name': region_name}
                    )
                    print(f"[KnowledgeBase] 知识图谱已同步到内存图: {city_name}")
                except Exception as gs_error:
                    print(f"[KnowledgeBase] 同步到内存图失败: {gs_error}")

            if postgis_saved:
                return True

            filename = f"{city_name}_kg.json"
            filepath = os.path.join(self.base_dir, filename)

            save_data = {
                'city_name': city_name,
                'region_name': region_name,
                'created_at': datetime.now().isoformat(),
                'kg_data': kg_data
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            print(f"[KnowledgeBase] 知识图谱已保存到文件: {city_name}")
            return True

        except Exception as e:
            print(f"[KnowledgeBase] 保存失败: {city_name}, 错误: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_kg(
        self,
        city_name: str,
        region_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        加载城市知识图谱

        策略：缓存 → PostGIS → 内存图 → 文件
        """
        cache_key = f"{city_name}:{region_name}" if region_name else city_name
        if cache_key in self._kg_cache:
            return self._kg_cache[cache_key]

        if self.postgis_available and city_name != 'general_low_altitude':
            try:
                kg_data = self._postgis_db.get_knowledge_graph(city_name, region_name)
                if kg_data:
                    self._kg_cache[cache_key] = kg_data
                    print(f"[KnowledgeBase] 已从 PostGIS 加载知识图谱: {city_name}")
                    return kg_data
            except Exception as pg_error:
                print(f"[KnowledgeBase] 从 PostGIS 加载失败: {pg_error}")

        if self.graph_store_available and city_name != 'general_low_altitude':
            try:
                kg_data = self._graph_store.load_knowledge_graph(city_name)
                if kg_data:
                    self._kg_cache[cache_key] = kg_data
                    print(f"[KnowledgeBase] 已从内存图加载知识图谱: {city_name}")
                    return kg_data
            except Exception:
                pass

        filename = f"{city_name}_kg.json"
        filepath = os.path.join(self.base_dir, filename)

        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    kg_data = saved_data.get('kg_data', {})
                    self._kg_cache[cache_key] = kg_data
                    print(f"[KnowledgeBase] 已从文件加载知识图谱: {city_name}")
                    return kg_data
            except Exception as e:
                print(f"[KnowledgeBase] 加载文件失败: {city_name}, 错误: {e}")

        return None

    def get_or_create_kg(
        self,
        city_name: str,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """获取或创建城市知识图谱"""
        existing_kg = self.load_kg(city_name)
        if existing_kg:
            return existing_kg

        print(f"[KnowledgeBase] 为城市 '{city_name}' 创建新的知识图谱...")
        dynamic_builder = get_dynamic_builder()
        kg = dynamic_builder.build_for_city(city_name, use_llm=use_llm)
        kg_dict = kg.to_dict()

        self.save_kg(city_name, kg_dict)

        return kg_dict

    def list_available_kgs(self) -> List[str]:
        """列出所有可用的知识图谱"""
        kgs = ['general_low_altitude']

        if self.graph_store_available:
            try:
                mem_cities = self._graph_store.list_cities()
                for city in mem_cities:
                    if city not in kgs and city != '__unified__':
                        kgs.append(city)
            except Exception:
                pass

        try:
            for filename in os.listdir(self.base_dir):
                if filename.endswith('_kg.json') and filename != 'general_low_altitude_kg.json':
                    city_name = filename.replace('_kg.json', '')
                    if city_name not in kgs:
                        kgs.append(city_name)
        except Exception:
            pass

        return kgs

    def delete_kg(self, city_name: str) -> bool:
        """删除城市知识图谱"""
        if city_name == 'general_low_altitude':
            print("[KnowledgeBase] 不能删除通用知识图谱")
            return False

        if city_name in self._kg_cache:
            del self._kg_cache[city_name]

        if self.graph_store_available:
            try:
                self._graph_store.delete_city(city_name)
            except Exception:
                pass

        filename = f"{city_name}_kg.json"
        filepath = os.path.join(self.base_dir, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"[KnowledgeBase] 已删除知识图谱: {city_name}")
                return True
            except Exception as e:
                print(f"[KnowledgeBase] 删除文件失败: {city_name}, 错误: {e}")
                return False

        return True

    def visualize_kg(
        self,
        city_name: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """可视化知识图谱"""
        if city_name == 'general_low_altitude':
            kg_data = self.get_general_kg()
            title = "通用低空空域风险评估知识图谱"
        else:
            kg_data = self.get_or_create_kg(city_name, use_llm=False)
            title = f"{city_name}低空空域风险评估知识图谱"

        if output_path is None:
            safe_name = city_name.replace(' ', '_').replace('/', '_')
            output_path = os.path.join(self.base_dir, 'images', f'{safe_name}_kg.png')

        visualizer = get_kg_visualizer()
        return visualizer.visualize_from_dict(kg_data, output_path, title)

    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        available_kgs = self.list_available_kgs()

        stats = {
            'total_kgs': len(available_kgs),
            'available_cities': [kg for kg in available_kgs if kg != 'general_low_altitude'],
            'has_general_kg': True,
            'storage_dir': self.base_dir,
            'postgis_available': self.postgis_available,
            'graph_store_available': self.graph_store_available,
            'graph_rag_available': self.graph_rag_available,
            'llm_available': self.llm_available,
            'last_updated': datetime.now().isoformat()
        }

        if self.graph_store_available:
            try:
                stats['graph_store'] = self._graph_store.get_statistics()
            except Exception:
                stats['graph_store'] = {'available': False}

        return stats

    def get_kb_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息（别名）"""
        return self.get_statistics()

    def get_rag_context(self, city_name: str) -> Optional[Dict[str, Any]]:
        """通过 GraphRAG 获取风险增强上下文"""
        if self.graph_rag_available:
            return self._graph_rag.get_context_for_report(city_name)
        return None

    def generate_with_llm(
        self,
        city_name: str,
        query: str
    ) -> Dict[str, Any]:
        """使用 GraphRAG + 本地LLM 增强生成"""
        if self.graph_rag_available:
            return self._graph_rag.generate_with_graph_rag(
                city_name, query, use_llm=self.llm_available
            )
        return {
            'success': False,
            'error': 'GraphRAG 不可用',
            'city_name': city_name
        }

    def build_case_kg(self) -> int:
        """从案例集构建完整知识图谱"""
        if self.graph_rag_available:
            return self._graph_rag.build_and_index_cases()
        return 0


_kb_instance = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库单例"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance


if __name__ == "__main__":
    print("=" * 60)
    print("测试 KnowledgeBase（PostGIS + 内存图 + GraphRAG）")
    print("=" * 60)

    kb = get_knowledge_base()

    print("\n知识库统计:")
    stats = kb.get_statistics()
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    print("\n可用知识图谱:")
    print(kb.list_available_kgs())

    print("\n测试获取通用知识图谱:")
    general_kg = kb.get_general_kg()
    print(f"节点数: {len(general_kg.get('entities', []))}")
    print(f"关系数: {len(general_kg.get('relations', []))}")

    print("\n测试创建城市知识图谱:")
    test_city = "武汉"
    city_kg = kb.get_or_create_kg(test_city, use_llm=False)
    print(f"节点数: {len(city_kg.get('entities', []))}")
    print(f"关系数: {len(city_kg.get('relations', []))}")

    print("\n测试完成！")