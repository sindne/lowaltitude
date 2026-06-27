"""
内存图存储引擎 — 纯 Python 实现
使用 KnowledgeGraph 数据结构在内存中管理图，支持：
- 多城市知识图谱的增删改查
- 子图检索与路径分析
- 语义搜索
- 与 PostGIS / JSON 文件的持久化同步
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Optional, Set, Tuple
from collections import deque
from datetime import datetime


class InMemoryGraphStore:
    """纯内存图存储引擎，不依赖任何外部图数据库"""

    def __init__(self):
        self._graphs: Dict[str, Dict[str, Any]] = {}
        self._entity_index: Dict[str, Dict[str, Any]] = {}
        self._relation_index: Dict[str, List[Dict[str, Any]]] = {}
        self._adjacency: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
        self._available = True
        print("[InMemoryGraph] 纯内存图存储引擎已就绪")

    @property
    def available(self) -> bool:
        return self._available

    def save_knowledge_graph(
        self,
        city_name: str,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """保存知识图谱到内存"""
        try:
            graph_data = {
                'city_name': city_name,
                'entities': entities,
                'relations': relations,
                'metadata': metadata or {},
                'updated_at': datetime.now().isoformat(),
                'entity_count': len(entities),
                'relation_count': len(relations)
            }
            self._graphs[city_name] = graph_data

            entity_map = {}
            for e in entities:
                eid = e.get('id', '')
                entity_map[eid] = e
                self._entity_index[eid] = e
            self._graphs[city_name]['_entity_map'] = entity_map

            adj = {}
            for r in relations:
                src = r.get('source_id', '')
                tgt = r.get('target_id', '')
                rtype = r.get('relation_type', '')
                if src not in adj:
                    adj[src] = []
                adj[src].append((tgt, rtype))
            self._adjacency[city_name] = adj

            self._relation_index[city_name] = relations

            print(f"[InMemoryGraph] 知识图谱已保存: {city_name} ({len(entities)} 实体, {len(relations)} 关系)")
            return True

        except Exception as e:
            print(f"[InMemoryGraph] 保存失败: {e}")
            return False

    def load_knowledge_graph(self, city_name: str) -> Optional[Dict[str, Any]]:
        """加载知识图谱"""
        graph = self._graphs.get(city_name)
        if not graph:
            return None

        return {
            'entities': graph.get('entities', []),
            'relations': graph.get('relations', []),
            'city_name': city_name,
            'metadata': graph.get('metadata', {})
        }

    def list_cities(self) -> List[str]:
        """列出所有已存储的城市"""
        return list(self._graphs.keys())

    def delete_city(self, city_name: str) -> bool:
        """删除城市知识图谱"""
        if city_name in self._graphs:
            del self._graphs[city_name]
            self._adjacency.pop(city_name, None)
            self._relation_index.pop(city_name, None)
            print(f"[InMemoryGraph] 已删除: {city_name}")
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_entities = 0
        total_relations = 0
        for city, graph in self._graphs.items():
            total_entities += graph.get('entity_count', len(graph.get('entities', [])))
            total_relations += graph.get('relation_count', len(graph.get('relations', [])))

        return {
            'available': True,
            'total_cities': len(self._graphs),
            'total_entities': total_entities,
            'total_relations': total_relations,
            'cities': self.list_cities()
        }

    def query_subgraph(
        self,
        city_name: str,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """查询指定城市的子图"""
        graph = self._graphs.get(city_name)
        if not graph:
            return {'entities': [], 'relations': []}

        entities = graph.get('entities', [])
        relations = graph.get('relations', [])
        return {'entities': list(entities), 'relations': list(relations)}

    def semantic_search(
        self,
        query_text: str,
        city_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """语义搜索实体"""
        results = []
        cities = [city_name] if city_name else list(self._graphs.keys())
        terms = query_text.lower().split()

        for city in cities:
            graph = self._graphs.get(city)
            if not graph:
                continue
            for entity in graph.get('entities', []):
                name = (entity.get('name', '') or '').lower()
                etype = (entity.get('entity_type', '') or '').lower()
                props = entity.get('properties', {}) or {}
                prop_values = ' '.join(
                    str(v) for v in props.values() if v is not None
                ).lower()
                searchable = f"{name} {etype} {prop_values}"
                if any(term in searchable for term in terms):
                    results.append({
                        'id': entity.get('id'),
                        'name': entity.get('name'),
                        'entity_type': entity.get('entity_type'),
                        'properties': props,
                        'city_name': city
                    })
                    if len(results) >= limit:
                        return results
        return results

    def get_connected_entities(
        self,
        entity_id: str,
        depth: int = 1
    ) -> Dict[str, Any]:
        """获取实体及其邻居"""
        entity = self._entity_index.get(entity_id)
        if not entity:
            return {'entity': None, 'relations': [], 'neighbors': []}

        neighbors = []
        relations = []
        rel_counter = 0

        for city, adj in self._adjacency.items():
            if entity_id in adj:
                for target_id, rtype in adj[entity_id]:
                    target = self._entity_index.get(target_id)
                    if target:
                        neighbors.append({
                            'id': target_id,
                            'name': target.get('name', ''),
                            'entity_type': target.get('entity_type', '')
                        })
                        relations.append({
                            'id': f'conn_rel_{rel_counter}',
                            'source_id': entity_id,
                            'target_id': target_id,
                            'relation_type': rtype,
                            'properties': {}
                        })
                        rel_counter += 1

        return {
            'entity': {
                'id': entity_id,
                'name': entity.get('name', ''),
                'entity_type': entity.get('entity_type', ''),
                'properties': entity.get('properties', {})
            },
            'relations': relations,
            'neighbors': neighbors
        }

    def find_paths(
        self,
        city_name: str,
        start_id: str,
        end_id: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """查找两个实体之间的路径"""
        adj = self._adjacency.get(city_name, {})
        entity_map = self._graphs.get(city_name, {}).get('_entity_map', {})
        paths = []

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
                paths.append({
                    'nodes': node_names,
                    'relation_types': rel_types
                })
                if len(paths) >= 3:
                    break
                continue

            for neighbor, rtype in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor], rel_types + [rtype]))

        return paths

    def clear(self):
        """清空所有数据"""
        self._graphs.clear()
        self._entity_index.clear()
        self._relation_index.clear()
        self._adjacency.clear()

    def close(self):
        """关闭（内存引擎无需关闭）"""
        pass


_graph_store: Optional[InMemoryGraphStore] = None


def get_graph_store() -> InMemoryGraphStore:
    """获取内存图存储单例"""
    global _graph_store
    if _graph_store is None:
        _graph_store = InMemoryGraphStore()
    return _graph_store


def reset_graph_store():
    """重置内存图存储"""
    global _graph_store
    if _graph_store:
        _graph_store.clear()
    _graph_store = None