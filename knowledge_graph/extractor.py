import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import List, Dict, Any, Optional
from knowledge_graph.schema import KnowledgeGraph, Entity, Relation, EntityType, RelationType

class StructuredInfoExtractor:
    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.kg = knowledge_graph
    
    def get_airspace_regions(self) -> List[Dict[str, Any]]:
        regions = self.kg.get_entities_by_type(EntityType.AIRSPACE_REGION)
        return [self._entity_to_dict(r) for r in regions]
    
    def get_risk_factors(self) -> List[Dict[str, Any]]:
        factors = self.kg.get_entities_by_type(EntityType.RISK_FACTOR)
        return [self._entity_to_dict(f) for f in factors]
    
    def get_infrastructure(self) -> List[Dict[str, Any]]:
        infrastructures = self.kg.get_entities_by_type(EntityType.INFRASTRUCTURE)
        return [self._entity_to_dict(i) for i in infrastructures]
    
    def get_sensitive_areas(self) -> List[Dict[str, Any]]:
        areas = self.kg.get_entities_by_type(EntityType.SENSITIVE_AREA)
        return [self._entity_to_dict(a) for a in areas]
    
    def get_weather_data(self) -> List[Dict[str, Any]]:
        weather = self.kg.get_entities_by_type(EntityType.WEATHER_DATA)
        return [self._entity_to_dict(w) for w in weather]
    
    def get_related_entities(self, entity_id: str) -> Dict[str, List[Dict[str, Any]]]:
        result = {'outgoing': [], 'incoming': []}
        outgoing_relations = self.kg.get_relations_by_source(entity_id)
        for rel in outgoing_relations:
            target_entity = self.kg.get_entity(rel.target_id)
            if target_entity:
                result['outgoing'].append({
                    'relation': rel.relation_type.value,
                    'entity': self._entity_to_dict(target_entity),
                    'properties': rel.properties
                })
        incoming_relations = self.kg.get_relations_by_target(entity_id)
        for rel in incoming_relations:
            source_entity = self.kg.get_entity(rel.source_id)
            if source_entity:
                result['incoming'].append({
                    'relation': rel.relation_type.value,
                    'entity': self._entity_to_dict(source_entity),
                    'properties': rel.properties
                })
        return result
    
    def get_risk_factors_for_region(self, region_id: str) -> List[Dict[str, Any]]:
        risk_factors = []
        relations = self.kg.get_relations_by_target(region_id)
        for rel in relations:
            if rel.relation_type == RelationType.INFLUENCES:
                factor_entity = self.kg.get_entity(rel.source_id)
                if factor_entity and factor_entity.entity_type == EntityType.RISK_FACTOR:
                    risk_factors.append({**self._entity_to_dict(factor_entity), 'relation_properties': rel.properties})
        return risk_factors
    
    def get_infrastructure_in_region(self, region_id: str) -> List[Dict[str, Any]]:
        infrastructures = []
        relations = self.kg.get_relations_by_target(region_id)
        for rel in relations:
            if rel.relation_type == RelationType.LOCATED_IN:
                infra_entity = self.kg.get_entity(rel.source_id)
                if infra_entity and infra_entity.entity_type == EntityType.INFRASTRUCTURE:
                    infrastructures.append(self._entity_to_dict(infra_entity))
        return infrastructures
    
    def extract_context_for_assessment(self, region_name: Optional[str] = None) -> Dict[str, Any]:
        context = {
            'airspace_regions': self.get_airspace_regions(),
            'risk_factors': self.get_risk_factors(),
            'infrastructure': self.get_infrastructure(),
            'sensitive_areas': self.get_sensitive_areas(),
            'weather_data': self.get_weather_data()
        }
        if region_name:
            for region in context['airspace_regions']:
                if region['name'] == region_name:
                    region_id = region['id']
                    context['target_region'] = region
                    context['related_risk_factors'] = self.get_risk_factors_for_region(region_id)
                    context['related_infrastructure'] = self.get_infrastructure_in_region(region_id)
                    break
        return context
    
    def _entity_to_dict(self, entity: Entity) -> Dict[str, Any]:
        result = entity.to_dict()
        for attr_name in dir(entity):
            if not attr_name.startswith('_') and attr_name not in ['id', 'name', 'entity_type', 'properties', 'to_dict', 'from_dict']:
                try:
                    value = getattr(entity, attr_name)
                    if not callable(value):
                        result[attr_name] = value
                except:
                    pass
        return result
