import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uuid
from typing import List, Dict, Any, Optional
from knowledge_graph.schema import KnowledgeGraph, Entity, Relation, EntityType, RelationType, AirspaceRegion, RiskFactor, Infrastructure, SensitiveArea, WeatherData

class KnowledgeGraphBuilder:
    def __init__(self):
        self.kg = KnowledgeGraph()
    
    def generate_id(self) -> str:
        return str(uuid.uuid4())
    
    def add_airspace_region(self, name: str, region_type: str, boundary: List[List[float]], min_altitude: float = 0.0, max_altitude: float = 1000.0, properties: Optional[Dict[str, Any]] = None) -> str:
        entity = AirspaceRegion(id=self.generate_id(), name=name, entity_type=EntityType.AIRSPACE_REGION, properties=properties or {}, region_type=region_type, boundary=boundary, min_altitude=min_altitude, max_altitude=max_altitude)
        self.kg.add_entity(entity)
        return entity.id
    
    def add_risk_factor(self, name: str, factor_type: str, weight: float, value: float, properties: Optional[Dict[str, Any]] = None) -> str:
        entity = RiskFactor(id=self.generate_id(), name=name, entity_type=EntityType.RISK_FACTOR, properties=properties or {}, factor_type=factor_type, weight=weight, value=value)
        self.kg.add_entity(entity)
        return entity.id
    
    def add_infrastructure(self, name: str, infra_type: str, location: List[float], properties: Optional[Dict[str, Any]] = None) -> str:
        entity = Infrastructure(id=self.generate_id(), name=name, entity_type=EntityType.INFRASTRUCTURE, properties=properties or {}, infra_type=infra_type, location=location)
        self.kg.add_entity(entity)
        return entity.id
    
    def add_sensitive_area(self, name: str, area_type: str, priority: int = 1, properties: Optional[Dict[str, Any]] = None) -> str:
        entity = SensitiveArea(id=self.generate_id(), name=name, entity_type=EntityType.SENSITIVE_AREA, properties=properties or {}, area_type=area_type, priority=priority)
        self.kg.add_entity(entity)
        return entity.id
    
    def add_weather_data(self, name: str, temperature: float, wind_speed: float, visibility: float, precipitation: float, timestamp: str, properties: Optional[Dict[str, Any]] = None) -> str:
        entity = WeatherData(id=self.generate_id(), name=name, entity_type=EntityType.WEATHER_DATA, properties=properties or {}, temperature=temperature, wind_speed=wind_speed, visibility=visibility, precipitation=precipitation, timestamp=timestamp)
        self.kg.add_entity(entity)
        return entity.id
    
    def add_relation(self, source_id: str, target_id: str, relation_type: RelationType, properties: Optional[Dict[str, Any]] = None) -> str:
        relation = Relation(id=self.generate_id(), source_id=source_id, target_id=target_id, relation_type=relation_type, properties=properties or {})
        self.kg.add_relation(relation)
        return relation.id
    
    def build(self) -> KnowledgeGraph:
        return self.kg
