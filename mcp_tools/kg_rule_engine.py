from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import deque

class RuleType(Enum):
    CONSTRAINT = '约束'
    PERMISSION = '许可'
    WARNING = '警告'
    RECOMMENDATION = '建议'

class RelationType(Enum):
    CONSTRAINTS = '约束'
    PERMITS = '许可'
    ADJACENT = '邻近'
    CONTAINS = '包含'
    BELONGS_TO = '属于'
    INFLUENCES = '影响'
    WARNING_FOR = '警告'

@dataclass
class KGEntity:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    entity_type: str = ''
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {'id': self.id, 'name': self.name, 'type': self.entity_type, 'properties': self.properties}

@dataclass
class KGRelation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ''
    target_id: str = ''
    relation_type: RelationType = RelationType.ADJACENT
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {'id': self.id, 'source': self.source_id, 'target': self.target_id, 'type': self.relation_type.value, 'properties': self.properties}

@dataclass
class InferenceRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    description: str = ''
    rule_type: RuleType = RuleType.WARNING
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    reference: str = ''

    def matches(self, entity: KGEntity, entities: Dict[str, KGEntity], relations: Dict[str, List[KGRelation]]) -> bool:
        if 'entity_type' in self.conditions:
            if entity.entity_type != self.conditions['entity_type']:
                return False
        if 'properties' in self.conditions:
            for key, value in self.conditions['properties'].items():
                if entity.properties.get(key) != value:
                    return False
        if 'has_relation' in self.conditions:
            required_relation = self.conditions['has_relation']
            has_relation = False
            for source_id, relation_list in relations.items():
                for relation in relation_list:
                    if relation.source_id == entity.id or relation.target_id == entity.id:
                        if relation.relation_type.value == required_relation.get('type'):
                            target_id = relation.target_id if relation.source_id == entity.id else relation.source_id
                            if target_id in entities and entities[target_id].entity_type == required_relation.get('target_type'):
                                has_relation = True
                                break
                if has_relation:
                    break
            if not has_relation:
                return False
        return True

    def apply(self, entity: KGEntity, entities: Dict[str, KGEntity], relations: Dict[str, List[KGRelation]]) -> Dict[str, Any]:
        result = {
            'rule_id': self.id,
            'rule_name': self.name,
            'rule_type': self.rule_type.value,
            'entity_id': entity.id,
            'entity_name': entity.name,
            'actions': {}
        }
        if 'set_properties' in self.actions:
            for key, value in self.actions['set_properties'].items():
                entity.properties[key] = value
                result['actions'][key] = value
        if 'create_relation' in self.actions:
            relation_spec = self.actions['create_relation']
            target_id = relation_spec.get('target_id')
            new_relation = KGRelation(
                source_id=entity.id,
                target_id=target_id,
                relation_type=RelationType(relation_spec.get('type')),
                properties=relation_spec.get('properties', {})
            )
            if entity.id not in relations:
                relations[entity.id] = []
            relations[entity.id].append(new_relation)
            result['actions']['new_relation'] = new_relation.to_dict()
        return result

class KGRuleEngine:
    def __init__(self):
        self.entities: Dict[str, KGEntity] = {}
        self.relations: Dict[str, List[KGRelation]] = {}
        self.target_relations: Dict[str, List[KGRelation]] = {}
        self.rules: List[InferenceRule] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        default_rules = [
            InferenceRule(
                name='禁飞区约束规则',
                description='禁飞区内禁止任何飞行活动',
                rule_type=RuleType.CONSTRAINT,
                conditions={'entity_type': '禁飞区'},
                actions={'set_properties': {'flight_prohibited': True, 'constraint_level': 'high'}},
                priority=100,
                reference='《民用无人机空中交通管理规定》'
            ),
            InferenceRule(
                name='机场净空区警告规则',
                description='机场净空区内飞行需满足高度要求',
                rule_type=RuleType.WARNING,
                conditions={'entity_type': '机场净空区'},
                actions={'set_properties': {'altitude_restriction': 120, 'warning_level': 'medium'}},
                priority=80,
                reference='《民用机场飞行区技术标准》'
            ),
            InferenceRule(
                name='敏感目标安全距离规则',
                description='需与敏感目标保持安全距离',
                rule_type=RuleType.CONSTRAINT,
                conditions={'entity_type': '敏感目标'},
                actions={'set_properties': {'safe_distance_km': 1.0, 'constraint_level': 'medium'}},
                priority=70,
                reference='《低空空域使用管理规定》'
            ),
            InferenceRule(
                name='人口密集区风险提示规则',
                description='人口密集区飞行风险较高',
                rule_type=RuleType.RECOMMENDATION,
                conditions={'entity_type': '人口密集区'},
                actions={'set_properties': {'risk_level': 'high', 'recommendation': '建议绕行或增加高度'}},
                priority=60,
                reference='《城市低空航路划设指南》'
            ),
            InferenceRule(
                name='邻近关系传播规则',
                description='邻近区域风险相互影响',
                rule_type=RuleType.WARNING,
                conditions={'has_relation': {'type': '邻近', 'target_type': '敏感目标'}},
                actions={'set_properties': {'adjacent_risk_influence': True, 'warning_level': 'low'}},
                priority=50,
                reference='《低空空域风险评估规范》'
            ),
            InferenceRule(
                name='约束关系继承规则',
                description='包含关系下约束继承',
                rule_type=RuleType.CONSTRAINT,
                conditions={'has_relation': {'type': '包含', 'target_type': '禁飞区'}},
                actions={'set_properties': {'inherited_constraint': True, 'constraint_level': 'inherited'}},
                priority=90,
                reference='《空域管理规定》'
            ),
        ]
        for rule in default_rules:
            self.add_rule(rule)

    def add_entity(self, entity: KGEntity) -> str:
        self.entities[entity.id] = entity
        return entity.id

    def add_relation(self, relation: KGRelation) -> str:
        if relation.source_id not in self.relations:
            self.relations[relation.source_id] = []
        self.relations[relation.source_id].append(relation)
        if relation.target_id not in self.target_relations:
            self.target_relations[relation.target_id] = []
        self.target_relations[relation.target_id].append(relation)
        return relation.id

    def add_rule(self, rule: InferenceRule) -> str:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)
        return rule.id

    def get_entity(self, entity_id: str) -> Optional[KGEntity]:
        return self.entities.get(entity_id)

    def get_relations_from(self, source_id: str) -> List[KGRelation]:
        return self.relations.get(source_id, [])

    def get_relations_to(self, target_id: str) -> List[KGRelation]:
        return self.target_relations.get(target_id, [])

    def find_path(self, start_id: str, end_id: str, max_depth: int = 5) -> Optional[List[KGRelation]]:
        if start_id == end_id:
            return []
        visited = set()
        queue = deque([(start_id, [])])
        while queue:
            current_id, path = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)
            if len(path) >= max_depth:
                continue
            for relation in self.get_relations_from(current_id):
                if relation.target_id == end_id:
                    return path + [relation]
                queue.append((relation.target_id, path + [relation]))
        return None

    def apply_rules(self, entity_id: Optional[str] = None) -> Dict[str, Any]:
        results = {'applied_rules': [], 'entity_updates': {}, 'new_relations': []}
        if entity_id:
            target_entities = [self.entities[entity_id]] if entity_id in self.entities else []
        else:
            target_entities = list(self.entities.values())
        for entity in target_entities:
            for rule in self.rules:
                if rule.matches(entity, self.entities, self.relations):
                    action_result = rule.apply(entity, self.entities, self.relations)
                    results['applied_rules'].append({
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'rule_type': rule.rule_type.value,
                        'entity_id': entity.id,
                        'entity_name': entity.name,
                        'reference': rule.reference
                    })
                    if entity.id not in results['entity_updates']:
                        results['entity_updates'][entity.id] = []
                    results['entity_updates'][entity.id].append(action_result)
        return results

    def check_compliance(self, flight_entities: List[str]) -> Dict[str, Any]:
        compliance_result = {'is_compliant': True, 'violations': [], 'warnings': [], 'recommendations': []}
        applied = self.apply_rules()
        for entity_id in flight_entities:
            entity = self.get_entity(entity_id)
            if entity is None:
                continue
            for rule_result in applied.get('applied_rules', []):
                if rule_result.get('entity_id') == entity_id:
                    rule_type_str = rule_result.get('rule_type', '')
                    info = {
                        'entity_id': entity.id,
                        'entity_name': entity.name,
                        'rule_id': rule_result.get('rule_id', ''),
                        'rule_name': rule_result.get('rule_name', ''),
                        'reference': rule_result.get('reference', '')
                    }
                    if rule_type_str == RuleType.CONSTRAINT.value:
                        compliance_result['is_compliant'] = False
                        compliance_result['violations'].append(info)
                    elif rule_type_str == RuleType.WARNING.value:
                        compliance_result['warnings'].append(info)
                    elif rule_type_str == RuleType.RECOMMENDATION.value:
                        info['recommendation'] = entity.properties.get('recommendation', '')
                        compliance_result['recommendations'].append(info)
        return compliance_result

    def export_graph(self) -> Dict[str, Any]:
        entities_list = [entity.to_dict() for entity in self.entities.values()]
        relations_list = []
        for source_id, relation_list in self.relations.items():
            for relation in relation_list:
                relations_list.append(relation.to_dict())
        return {'entities': entities_list, 'relations': relations_list}

    def import_graph(self, graph_data: Dict[str, Any]):
        for entity_data in graph_data.get('entities', []):
            entity = KGEntity(
                id=entity_data.get('id'),
                name=entity_data.get('name'),
                entity_type=entity_data.get('type'),
                properties=entity_data.get('properties', {})
            )
            self.add_entity(entity)
        for relation_data in graph_data.get('relations', []):
            relation = KGRelation(
                id=relation_data.get('id'),
                source_id=relation_data.get('source'),
                target_id=relation_data.get('target'),
                relation_type=RelationType(relation_data.get('type')),
                properties=relation_data.get('properties', {})
            )
            self.add_relation(relation)

_kg_rule_engine_instance = None

def get_kg_rule_engine() -> KGRuleEngine:
    global _kg_rule_engine_instance
    if _kg_rule_engine_instance is None:
        _kg_rule_engine_instance = KGRuleEngine()
    return _kg_rule_engine_instance
