from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class EntityType(Enum):
    AIRSPACE_REGION = 'airspace_region'
    RISK_FACTOR = 'risk_factor'
    INFRASTRUCTURE = 'infrastructure'
    SENSITIVE_AREA = 'sensitive_area'
    WEATHER_DATA = 'weather_data'
    REGULATION = 'regulation'
    SENSOR = 'sensor'
    AIRCRAFT = 'aircraft'
    FLIGHT_ROUTE = 'flight_route'
    FLIGHT_LOG = 'flight_log'
    FLIGHT_IMAGE = 'flight_image'
    RESTRICTION_ZONE = 'restriction_zone'
    NAVIGATION_AID = 'navigation_aid'
    COMMUNICATION_FACILITY = 'communication_facility'

class RelationType(Enum):
    CONTAINS = 'contains'
    INFLUENCES = 'influences'
    LOCATED_IN = 'located_in'
    ADJACENT_TO = 'adjacent_to'
    ASSOCIATED_WITH = 'associated_with'
    GOVERNS = 'governs'
    MONITORS = 'monitors'
    OPERATES_IN = 'operates_in'
    FOLLOWS = 'follows'
    RECORDS = 'records'
    CAPTURES = 'captures'
    RESTRICTS = 'restricts'
    AIDS = 'aids'
    CONNECTS = 'connects'
    APPLIES_TO = 'applies_to'
    USES = 'uses'
    DEPENDS_ON = 'depends_on'

@dataclass
class Entity:
    id: str = ''
    name: str = ''
    entity_type: EntityType = EntityType.AIRSPACE_REGION
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'entity_type': self.entity_type.value,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        return cls(
            id=data['id'],
            name=data['name'],
            entity_type=EntityType(data['entity_type']),
            properties=data.get('properties', {})
        )

@dataclass
class Relation:
    id: str = ''
    source_id: str = ''
    target_id: str = ''
    relation_type: RelationType = RelationType.ASSOCIATED_WITH
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relation_type': self.relation_type.value,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relation':
        return cls(
            id=data['id'],
            source_id=data['source_id'],
            target_id=data['target_id'],
            relation_type=RelationType(data['relation_type']),
            properties=data.get('properties', {})
        )

@dataclass
class AirspaceRegion(Entity):
    region_type: str = ''
    boundary: List[List[float]] = field(default_factory=list)
    min_altitude: float = 0.0
    max_altitude: float = 1000.0
    
    def __post_init__(self):
        self.entity_type = EntityType.AIRSPACE_REGION
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            'region_type': self.region_type,
            'boundary': self.boundary,
            'min_altitude': self.min_altitude,
            'max_altitude': self.max_altitude
        })
        return base_dict

@dataclass
class RiskFactor(Entity):
    factor_type: str = ''
    weight: float = 0.0
    value: float = 0.0
    
    def __post_init__(self):
        self.entity_type = EntityType.RISK_FACTOR
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            'factor_type': self.factor_type,
            'weight': self.weight,
            'value': self.value
        })
        return base_dict

@dataclass
class Infrastructure(Entity):
    infra_type: str = ''
    location: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        self.entity_type = EntityType.INFRASTRUCTURE
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            'infra_type': self.infra_type,
            'location': self.location
        })
        return base_dict

@dataclass
class SensitiveArea(Entity):
    area_type: str = ''
    priority: int = 1
    
    def __post_init__(self):
        self.entity_type = EntityType.SENSITIVE_AREA
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            'area_type': self.area_type,
            'priority': self.priority
        })
        return base_dict

@dataclass
class WeatherData(Entity):
    temperature: float = 0.0
    wind_speed: float = 0.0
    visibility: float = 10.0
    precipitation: float = 0.0
    timestamp: str = ''
    
    def __post_init__(self):
        self.entity_type = EntityType.WEATHER_DATA
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            'temperature': self.temperature,
            'wind_speed': self.wind_speed,
            'visibility': self.visibility,
            'precipitation': self.precipitation,
            'timestamp': self.timestamp
        })
        return base_dict

@dataclass
class Regulation(Entity):
    regulation_type: str = ''
    issue_date: str = ''
    effective_date: str = ''
    content_summary: str = ''
    restrictions: List[str] = field(default_factory=list)
    url: str = ''
    
    def __post_init__(self):
        self.entity_type = EntityType.REGULATION

@dataclass
class Sensor(Entity):
    sensor_type: str = ''
    model: str = ''
    manufacturer: str = ''
    detection_range: float = 0.0
    accuracy: float = 0.0
    update_rate: float = 0.0
    installation_location: List[float] = field(default_factory=list)
    status: str = 'active'
    
    def __post_init__(self):
        self.entity_type = EntityType.SENSOR

@dataclass
class Aircraft(Entity):
    aircraft_type: str = ''
    model: str = ''
    manufacturer: str = ''
    max_altitude: float = 0.0
    max_speed: float = 0.0
    payload_capacity: float = 0.0
    flight_duration: float = 0.0
    registration_number: str = ''
    
    def __post_init__(self):
        self.entity_type = EntityType.AIRCRAFT

@dataclass
class FlightRoute(Entity):
    route_number: str = ''
    start_point: List[float] = field(default_factory=list)
    end_point: List[float] = field(default_factory=list)
    waypoints: List[List[float]] = field(default_factory=list)
    total_distance: float = 0.0
    estimated_duration: float = 0.0
    cruise_altitude: float = 0.0
    restriction_level: str = 'normal'
    
    def __post_init__(self):
        self.entity_type = EntityType.FLIGHT_ROUTE

@dataclass
class FlightLog(Entity):
    flight_id: str = ''
    aircraft_id: str = ''
    route_id: str = ''
    start_time: str = ''
    end_time: str = ''
    pilot: str = ''
    weather_conditions: str = ''
    incidents: List[str] = field(default_factory=list)
    fuel_consumption: float = 0.0
    notes: str = ''
    
    def __post_init__(self):
        self.entity_type = EntityType.FLIGHT_LOG

@dataclass
class FlightImage(Entity):
    image_id: str = ''
    capture_time: str = ''
    capture_location: List[float] = field(default_factory=list)
    camera_type: str = ''
    resolution: str = ''
    image_type: str = ''
    file_path: str = ''
    description: str = ''
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.entity_type = EntityType.FLIGHT_IMAGE

@dataclass
class RestrictionZone(Entity):
    zone_type: str = ''
    restriction_level: str = ''
    boundary: List[List[float]] = field(default_factory=list)
    min_altitude: float = 0.0
    max_altitude: float = 1000.0
    effective_time: str = ''
    reason: str = ''
    authority: str = ''
    
    def __post_init__(self):
        self.entity_type = EntityType.RESTRICTION_ZONE

@dataclass
class NavigationAid(Entity):
    aid_type: str = ''
    frequency: str = ''
    location: List[float] = field(default_factory=list)
    range: float = 0.0
    status: str = 'active'
    last_maintenance: str = ''
    
    def __post_init__(self):
        self.entity_type = EntityType.NAVIGATION_AID

@dataclass
class CommunicationFacility(Entity):
    facility_type: str = ''
    frequency: str = ''
    location: List[float] = field(default_factory=list)
    coverage_range: float = 0.0
    transmission_power: float = 0.0
    status: str = 'active'
    
    def __post_init__(self):
        self.entity_type = EntityType.COMMUNICATION_FACILITY

class KnowledgeGraph:
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.entity_counter = 0
        self.relation_counter = 0
    
    def add_entity(self, entity: Entity) -> str:
        self.entities[entity.id] = entity
        return entity.id
    
    def add_relation(self, relation: Relation) -> str:
        self.relations[relation.id] = relation
        return relation.id
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        return [e for e in self.entities.values() if e.entity_type == entity_type]
    
    def get_relations_by_source(self, source_id: str) -> List[Relation]:
        return [r for r in self.relations.values() if r.source_id == source_id]
    
    def get_relations_by_target(self, target_id: str) -> List[Relation]:
        return [r for r in self.relations.values() if r.target_id == target_id]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entities': [e.to_dict() for e in self.entities.values()],
            'relations': [r.to_dict() for r in self.relations.values()]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeGraph':
        kg = cls()
        for entity_data in data.get('entities', []):
            entity_type = EntityType(entity_data.get('entity_type'))
            entity = None
            if entity_type == EntityType.AIRSPACE_REGION:
                entity = AirspaceRegion(
                    id=entity_data.get('id', ''),
                    name=entity_data.get('name', ''),
                    entity_type=entity_type,
                    properties=entity_data.get('properties', {}),
                    region_type=entity_data.get('region_type', ''),
                    boundary=entity_data.get('boundary', []),
                    min_altitude=entity_data.get('min_altitude', 0.0),
                    max_altitude=entity_data.get('max_altitude', 1000.0)
                )
            elif entity_type == EntityType.RISK_FACTOR:
                entity = RiskFactor(
                    id=entity_data.get('id', ''),
                    name=entity_data.get('name', ''),
                    entity_type=entity_type,
                    properties=entity_data.get('properties', {}),
                    factor_type=entity_data.get('factor_type', ''),
                    weight=entity_data.get('weight', 0.0),
                    value=entity_data.get('value', 0.0)
                )
            elif entity_type == EntityType.INFRASTRUCTURE:
                entity = Infrastructure(
                    id=entity_data.get('id', ''),
                    name=entity_data.get('name', ''),
                    entity_type=entity_type,
                    properties=entity_data.get('properties', {}),
                    infra_type=entity_data.get('infra_type', ''),
                    location=entity_data.get('location', [])
                )
            elif entity_type == EntityType.SENSITIVE_AREA:
                entity = SensitiveArea(
                    id=entity_data.get('id', ''),
                    name=entity_data.get('name', ''),
                    entity_type=entity_type,
                    properties=entity_data.get('properties', {}),
                    area_type=entity_data.get('area_type', ''),
                    priority=entity_data.get('priority', 1)
                )
            elif entity_type == EntityType.WEATHER_DATA:
                entity = WeatherData(
                    id=entity_data.get('id', ''),
                    name=entity_data.get('name', ''),
                    entity_type=entity_type,
                    properties=entity_data.get('properties', {}),
                    temperature=entity_data.get('temperature', 0.0),
                    wind_speed=entity_data.get('wind_speed', 0.0),
                    visibility=entity_data.get('visibility', 10.0),
                    precipitation=entity_data.get('precipitation', 0.0),
                    timestamp=entity_data.get('timestamp', '')
                )
            else:
                entity = Entity.from_dict(entity_data)
            if entity:
                kg.add_entity(entity)
        for relation_data in data.get('relations', []):
            kg.add_relation(Relation.from_dict(relation_data))
        return kg
