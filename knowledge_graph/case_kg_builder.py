"""
案例集知识图谱构建器
从历史风险评估案例中提取实体和关系，构建完整的案例知识图谱
"""

import sys
import os
import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.schema import (
    Entity, Relation, KnowledgeGraph, EntityType, RelationType,
    AirspaceRegion, RiskFactor, Infrastructure, SensitiveArea, WeatherData
)
from knowledge_graph.builder import KnowledgeGraphBuilder


class CaseKnowledgeGraphBuilder:
    """
    案例集知识图谱构建器

    从以下数据源构建知识图谱：
    1. SQLite 评估数据库 (data/risk_assessment.db)
    2. PostGIS 评估历史
    3. JSON 知识图谱文件 (data/knowledge_base/)
    4. 动态知识图谱构建器
    """

    def __init__(self):
        self._cases: List[Dict[str, Any]] = []
        self._postgis_db = None
        self._dynamic_builder = None
        self._loaded_cities: set = set()

    def set_postgis_db(self, db):
        self._postgis_db = db

    def set_dynamic_builder(self, builder):
        self._dynamic_builder = builder

    def load_cases_from_sqlite(self, db_path: str = "./data/risk_assessment.db") -> int:
        """从 SQLite 数据库加载案例"""
        count = 0
        try:
            if not os.path.exists(db_path):
                print(f"[CaseKGBuilder] SQLite 数据库不存在: {db_path}")
                return 0

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='assessments'"
            )
            if cursor.fetchone():
                cursor.execute(
                    "SELECT * FROM assessments ORDER BY created_at DESC LIMIT 100"
                )
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    case = dict(zip(columns, row))
                    self._cases.append({
                        'id': str(case.get('id', '')),
                        'city': case.get('region', case.get('city', '')),
                        'risk_level': case.get('risk_level', ''),
                        'data': case,
                        'source': 'sqlite'
                    })
                    count += 1

            conn.close()
            print(f"[CaseKGBuilder] 从 SQLite 加载了 {count} 条案例")
        except Exception as e:
            print(f"[CaseKGBuilder] SQLite 加载失败: {e}")

        return count

    def load_cases_from_postgis(self) -> int:
        """从 PostGIS 数据库加载案例"""
        count = 0
        if not self._postgis_db:
            return 0

        try:
            cases = self._postgis_db.get_assessment_history(limit=100)
            if cases:
                for case in cases:
                    self._cases.append({
                        'id': str(case.get('id', '')),
                        'city': case.get('city_name', case.get('region', '')),
                        'risk_level': case.get('risk_level', ''),
                        'data': case,
                        'source': 'postgis'
                    })
                    count += 1
            print(f"[CaseKGBuilder] 从 PostGIS 加载了 {count} 条案例")
        except Exception as e:
            print(f"[CaseKGBuilder] PostGIS 加载失败: {e}")

        return count

    def load_cases_from_json(self, base_dir: str = "./data/knowledge_base") -> int:
        """从 JSON 知识图谱文件加载案例"""
        count = 0
        try:
            if not os.path.exists(base_dir):
                return 0

            for filename in os.listdir(base_dir):
                if filename.endswith('_kg.json') and 'general' not in filename:
                    filepath = os.path.join(base_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            city_name = data.get('city_name', filename.replace('_kg.json', ''))
                            kg_data = data.get('kg_data', {})

                            self._cases.append({
                                'id': f"json_{city_name}",
                                'city': city_name,
                                'risk_level': '',
                                'kg_data': kg_data,
                                'data': data,
                                'source': 'json'
                            })
                            count += 1
                    except Exception:
                        pass

            print(f"[CaseKGBuilder] 从 JSON 加载了 {count} 条案例")
        except Exception as e:
            print(f"[CaseKGBuilder] JSON 加载失败: {e}")

        return count

    def load_all_cases(
        self,
        sqlite_path: str = "./data/risk_assessment.db",
        json_dir: str = "./data/knowledge_base"
    ) -> int:
        """加载所有来源的案例"""
        total = 0
        total += self.load_cases_from_sqlite(sqlite_path)
        total += self.load_cases_from_postgis()
        total += self.load_cases_from_json(json_dir)
        print(f"[CaseKGBuilder] 共加载 {total} 条案例")
        return total

    def get_cases(self) -> List[Dict[str, Any]]:
        """获取所有案例"""
        return self._cases

    def get_cases_by_city(self, city_name: str) -> List[Dict[str, Any]]:
        """按城市筛选案例"""
        return [
            c for c in self._cases
            if city_name in (c.get('city', '') or '')
        ]

    def build_unified_kg(self) -> KnowledgeGraph:
        """
        从所有案例构建统一知识图谱

        Returns:
            合并所有案例实体的完整知识图谱
        """
        builder = KnowledgeGraphBuilder()
        entity_map: Dict[str, str] = {}
        city_entities: Dict[str, str] = {}
        risk_factor_summary: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'count': 0, 'weights': [], 'values': []}
        )
        infrastructure_summary: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'count': 0, 'locations': []}
        )
        sensitive_area_summary: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'count': 0, 'priorities': []}
        )

        for case in self._cases:
            city_name = case.get('city', '')
            if not city_name:
                continue

            kg_data = case.get('kg_data', {})
            if not kg_data:
                data = case.get('data', {})
                if isinstance(data, dict):
                    kg_data = data.get('kg_data', data.get('risk_data', {}).get('knowledge_graph', {}))

            entities = kg_data.get('entities', [])
            relations = kg_data.get('relations', [])

            if city_name not in city_entities:
                city_id = builder.add_airspace_region(
                    name=city_name,
                    region_type='city',
                    boundary=[],
                    properties={'source': case.get('source', 'unknown')}
                )
                city_entities[city_name] = city_id

            city_id = city_entities[city_name]

            for entity in entities:
                eid = entity.get('id', '')
                etype = entity.get('entity_type', '')
                name = entity.get('name', '')
                props = entity.get('properties', {})

                if eid in entity_map:
                    continue

                new_id = None
                if etype == 'risk_factor':
                    new_id = builder.add_risk_factor(
                        name=name,
                        factor_type=props.get('factor_type', ''),
                        weight=props.get('weight', 0),
                        value=props.get('value', 0),
                        properties=props
                    )
                    risk_factor_summary[name]['count'] += 1
                    risk_factor_summary[name]['weights'].append(props.get('weight', 0))
                    risk_factor_summary[name]['values'].append(props.get('value', 0))

                    builder.add_relation(city_id, new_id, RelationType.ASSOCIATED_WITH)

                elif etype == 'infrastructure':
                    new_id = builder.add_infrastructure(
                        name=name,
                        infra_type=props.get('infra_type', entity.get('entity_type', '')),
                        location=entity.get('location', []),
                        properties=props
                    )
                    infrastructure_summary[name]['count'] += 1
                    infrastructure_summary[name]['locations'].append(
                        entity.get('location', [])
                    )

                    builder.add_relation(city_id, new_id, RelationType.CONTAINS)

                elif etype == 'sensitive_area':
                    new_id = builder.add_sensitive_area(
                        name=name,
                        area_type=props.get('area_type', entity.get('entity_type', '')),
                        priority=props.get('priority', 2),
                        properties=props
                    )
                    sensitive_area_summary[name]['count'] += 1
                    sensitive_area_summary[name]['priorities'].append(
                        props.get('priority', 2)
                    )

                    builder.add_relation(city_id, new_id, RelationType.CONTAINS)

                elif etype == 'airspace_region' and name != city_name:
                    new_id = builder.add_airspace_region(
                        name=name,
                        region_type=props.get('region_type', 'subdistrict'),
                        properties=props
                    )
                    builder.add_relation(city_id, new_id, RelationType.CONTAINS)

                if new_id:
                    entity_map[eid] = new_id

            for relation in relations:
                src_id = relation.get('source_id', '')
                tgt_id = relation.get('target_id', '')
                rtype_str = relation.get('relation_type', '')

                mapped_src = entity_map.get(src_id, src_id)
                mapped_tgt = entity_map.get(tgt_id, tgt_id)

                try:
                    rtype = RelationType(rtype_str)
                except ValueError:
                    rtype = RelationType.ASSOCIATED_WITH

                builder.add_relation(
                    mapped_src, mapped_tgt, rtype,
                    properties=relation.get('properties', {})
                )

        kg = builder.build()
        kg.properties = {
            'risk_factor_summary': dict(risk_factor_summary),
            'infrastructure_summary': dict(infrastructure_summary),
            'sensitive_area_summary': dict(sensitive_area_summary),
            'city_count': len(city_entities),
            'case_count': len(self._cases)
        }

        print(f"[CaseKGBuilder] 统一知识图谱已构建: "
              f"{len(kg.entities)} 实体, {len(kg.relations)} 关系, "
              f"{len(city_entities)} 城市, {len(self._cases)} 案例")

        return kg

    def build_city_kg(
        self,
        city_name: str,
        merge_cases: bool = True
    ) -> KnowledgeGraph:
        """
        为指定城市构建知识图谱

        Args:
            city_name: 城市名称
            merge_cases: 是否合并多个案例的实体

        Returns:
            城市知识图谱
        """
        city_cases = self.get_cases_by_city(city_name)

        if not city_cases:
            if self._dynamic_builder:
                print(f"[CaseKGBuilder] 城市 '{city_name}' 无案例数据，使用动态构建器")
                return self._dynamic_builder.build_for_city(city_name)
            from knowledge_graph.dynamic_builder import get_dynamic_builder
            return get_dynamic_builder().build_for_city(city_name)

        builder = KnowledgeGraphBuilder()

        city_id = builder.add_airspace_region(
            name=city_name,
            region_type='city',
            properties={'case_count': len(city_cases)}
        )

        entity_ids: Dict[str, str] = {}

        for case in city_cases:
            kg_data = case.get('kg_data', {})
            if not kg_data:
                data = case.get('data', {})
                if isinstance(data, dict):
                    kg_data = data.get('kg_data', data.get('risk_data', {}).get('knowledge_graph', {}))

            entities = kg_data.get('entities', [])
            relations = kg_data.get('relations', [])

            for entity in entities:
                eid = entity.get('id', '')
                name = entity.get('name', '')
                etype = entity.get('entity_type', '')

                if name in entity_ids:
                    continue

                if etype == 'risk_factor':
                    props = entity.get('properties', {})
                    fid = builder.add_risk_factor(
                        name=name,
                        factor_type=props.get('factor_type', ''),
                        weight=props.get('weight', 0),
                        value=props.get('value', 0),
                        properties=props
                    )
                    entity_ids[name] = fid
                    builder.add_relation(city_id, fid, RelationType.ASSOCIATED_WITH)

                elif etype == 'infrastructure':
                    fid = builder.add_infrastructure(
                        name=name,
                        infra_type=entity.get('properties', {}).get('infra_type', ''),
                        location=entity.get('location', []),
                        properties=entity.get('properties', {})
                    )
                    entity_ids[name] = fid
                    builder.add_relation(city_id, fid, RelationType.CONTAINS)

                elif etype == 'sensitive_area':
                    fid = builder.add_sensitive_area(
                        name=name,
                        area_type=entity.get('properties', {}).get('area_type', ''),
                        priority=entity.get('properties', {}).get('priority', 2),
                        properties=entity.get('properties', {})
                    )
                    entity_ids[name] = fid
                    builder.add_relation(city_id, fid, RelationType.CONTAINS)

            for relation in relations:
                src_id = relation.get('source_id', '')
                tgt_id = relation.get('target_id', '')
                rtype_str = relation.get('relation_type', '')

                src_name = self._find_entity_name(entities, src_id)
                tgt_name = self._find_entity_name(entities, tgt_id)

                mapped_src = None
                mapped_tgt = None

                if src_name in entity_ids:
                    mapped_src = entity_ids[src_name]
                if tgt_name in entity_ids:
                    mapped_tgt = entity_ids[tgt_name]

                if mapped_src and mapped_tgt:
                    try:
                        rtype = RelationType(rtype_str)
                    except ValueError:
                        rtype = RelationType.ASSOCIATED_WITH
                    builder.add_relation(mapped_src, mapped_tgt, rtype)

        kg = builder.build()
        print(f"[CaseKGBuilder] 城市 '{city_name}' 知识图谱: "
              f"{len(kg.entities)} 实体, {len(kg.relations)} 关系")
        return kg

    def get_case_statistics(self) -> Dict[str, Any]:
        """获取案例集统计信息"""
        cities = set()
        risk_levels = defaultdict(int)
        sources = defaultdict(int)

        for case in self._cases:
            city = case.get('city', '')
            if city:
                cities.add(city)
            risk_levels[case.get('risk_level', '未知')] += 1
            sources[case.get('source', 'unknown')] += 1

        return {
            'total_cases': len(self._cases),
            'total_cities': len(cities),
            'cities': sorted(list(cities)),
            'risk_level_distribution': dict(risk_levels),
            'source_distribution': dict(sources)
        }

    def _find_entity_name(
        self,
        entities: List[Dict[str, Any]],
        entity_id: str
    ) -> Optional[str]:
        """通过ID查找实体名称"""
        for e in entities:
            if e.get('id') == entity_id:
                return e.get('name')
        return None


_case_kg_builder: Optional[CaseKnowledgeGraphBuilder] = None


def get_case_kg_builder() -> CaseKnowledgeGraphBuilder:
    """获取案例知识图谱构建器单例"""
    global _case_kg_builder
    if _case_kg_builder is None:
        _case_kg_builder = CaseKnowledgeGraphBuilder()
    return _case_kg_builder