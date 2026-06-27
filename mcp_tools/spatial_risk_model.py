import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

class RiskLevel(Enum):
    SAFE = '安全'
    LOW = '低风险'
    MEDIUM = '中等风险'
    HIGH = '高风险'
    CRITICAL = '极高风险'

    @classmethod
    def from_score(cls, score: float) -> 'RiskLevel':
        if score >= 0.8:
            return cls.CRITICAL
        elif score >= 0.6:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        elif score >= 0.2:
            return cls.LOW
        else:
            return cls.SAFE

class SpatialEntityType(Enum):
    NO_FLY_ZONE = '禁飞区'
    TEMPORARY_RESTRICTION = '临时限飞区'
    AIRPORT_CLEARANCE = '机场净空区'
    POPULATION_TARGET = '人口密集区'
    SENSITIVE_TARGET = '敏感目标'
    OBSTACLE = '障碍物'
    TERRAIN = '地形'
    WIND_FIELD = '风场'

@dataclass
class Point:
    lng: float = 0.0
    lat: float = 0.0

    def to_list(self) -> List[float]:
        return [self.lng, self.lat]

    @classmethod
    def from_list(cls, coords: List[float]) -> 'Point':
        return cls(lng=coords[0], lat=coords[1])

@dataclass
class Polygon:
    coordinates: List[List[float]] = field(default_factory=list)

    def to_list(self) -> List[List[float]]:
        return self.coordinates

    @classmethod
    def from_list(cls, coords: List[List[float]]) -> 'Polygon':
        return cls(coordinates=coords)

@dataclass
class SpatialRiskEntity:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    entity_type: SpatialEntityType = SpatialEntityType.NO_FLY_ZONE
    geometry: Any = None
    properties: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.SAFE

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'entity_type': self.entity_type.value,
            'geometry': self.geometry.to_list() if hasattr(self.geometry, 'to_list') else None,
            'properties': self.properties,
            'risk_score': self.risk_score,
            'risk_level': self.risk_level.value
        }

@dataclass
class FlightPlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    waypoints: List[Point] = field(default_factory=list)
    altitude: float = 100.0
    start_time: str = ''
    end_time: str = ''
    aircraft_type: str = '无人机'

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        lngs = [p.lng for p in self.waypoints]
        lats = [p.lat for p in self.waypoints]
        return (min(lngs), min(lats), max(lngs), max(lats))

@dataclass
class ComplianceRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    description: str = ''
    rule_type: str = ''
    conditions: Dict[str, Any] = field(default_factory=dict)
    penalty: float = 0.0
    reference: str = ''

class SpatialRiskModel:
    def __init__(self):
        self.earth_radius = 6371.0
        self.risk_entities: List[SpatialRiskEntity] = []
        self.compliance_rules: List[ComplianceRule] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        default_rules = [
            ComplianceRule(
                name='禁飞区禁令',
                description='禁止在禁飞区内飞行',
                rule_type='prohibited',
                conditions={'entity_type': '禁飞区', 'distance_km': 0.0},
                penalty=1.0,
                reference='《民用无人机空中交通管理规定》'
            ),
            ComplianceRule(
                name='机场净空区限制',
                description='机场净空区内飞行高度受限',
                rule_type='restricted',
                conditions={'entity_type': '机场净空区', 'max_altitude': 120.0},
                penalty=0.5,
                reference='《民用机场飞行区技术标准》'
            ),
            ComplianceRule(
                name='敏感目标安全距离',
                description='需与敏感目标保持安全距离',
                rule_type='restricted',
                conditions={'entity_type': '敏感目标', 'safe_distance_km': 1.0},
                penalty=0.3,
                reference='《低空空域使用管理规定》'
            ),
            ComplianceRule(
                name='人口密集区风险',
                description='人口密集区飞行风险较高',
                rule_type='recommended',
                conditions={'entity_type': '人口密集区', 'warning_distance_km': 2.0},
                penalty=0.2,
                reference='《城市低空航路划设指南》'
            ),
        ]
        self.compliance_rules = default_rules

    def calculate_haversine_distance(self, point1: Point, point2: Point) -> float:
        lat1_rad = math.radians(point1.lat)
        lat2_rad = math.radians(point2.lat)
        delta_lat = math.radians(point2.lat - point1.lat)
        delta_lng = math.radians(point2.lng - point1.lng)
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return self.earth_radius * c

    def point_in_polygon_ray_casting(self, point: Point, polygon: Polygon) -> bool:
        x, y = (point.lng, point.lat)
        inside = False
        coords = polygon.coordinates
        n = len(coords)
        j = n - 1
        for i in range(n):
            xi, yi = coords[i]
            xj, yj = coords[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def buffer_point(self, point: Point, radius_km: float, num_points: int = 32) -> Polygon:
        coordinates = []
        km_per_degree_lng = 111.32 * math.cos(math.radians(point.lat))
        km_per_degree_lat = 110.574
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            delta_lng = radius_km * math.cos(angle) / km_per_degree_lng
            delta_lat = radius_km * math.sin(angle) / km_per_degree_lat
            coordinates.append([point.lng + delta_lng, point.lat + delta_lat])
        coordinates.append(coordinates[0])
        return Polygon(coordinates=coordinates)

    def buffer_polygon(self, polygon: Polygon, radius_km: float) -> Polygon:
        centroid = self.calculate_polygon_centroid(polygon)
        return self.buffer_point(centroid, radius_km)

    def overlay_intersection(self, polygon1: Polygon, polygon2: Polygon) -> Optional[Polygon]:
        bbox1 = self.calculate_bounding_box(polygon1)
        bbox2 = self.calculate_bounding_box(polygon2)
        if bbox1[2] < bbox2[0] or bbox2[2] < bbox1[0] or bbox1[3] < bbox2[1] or bbox2[3] < bbox1[1]:
            return None
        centroid1 = self.calculate_polygon_centroid(polygon1)
        centroid2 = self.calculate_polygon_centroid(polygon2)
        avg_lng = (centroid1.lng + centroid2.lng) / 2
        avg_lat = (centroid1.lat + centroid2.lat) / 2
        return self.buffer_point(Point(avg_lng, avg_lat), 2.0)

    def overlay_union(self, polygon1: Polygon, polygon2: Polygon) -> Polygon:
        bbox1 = self.calculate_bounding_box(polygon1)
        bbox2 = self.calculate_bounding_box(polygon2)
        min_lng = min(bbox1[0], bbox2[0])
        min_lat = min(bbox1[1], bbox2[1])
        max_lng = max(bbox1[2], bbox2[2])
        max_lat = max(bbox1[3], bbox2[3])
        center_lng = (min_lng + max_lng) / 2
        center_lat = (min_lat + max_lat) / 2
        radius_km = max(self.calculate_haversine_distance(Point(min_lng, min_lat), Point(max_lng, max_lat)) / 2, 5.0)
        return self.buffer_point(Point(center_lng, center_lat), radius_km)

    def raster_reclassify(self, risk_scores: List[float], bins: int = 5) -> List[int]:
        min_score = min(risk_scores)
        max_score = max(risk_scores)
        if max_score == min_score:
            return [bins // 2] * len(risk_scores)
        bin_width = (max_score - min_score) / bins
        classifications = []
        for score in risk_scores:
            bin_idx = min(int((score - min_score) / bin_width), bins - 1)
            classifications.append(bin_idx)
        return classifications

    def viewshed_analysis(self, observer: Point, terrain_height: float, target_height: float, max_distance_km: float = 10.0) -> Dict[str, Any]:
        visible_area = self.buffer_point(observer, max_distance_km)
        return {'visible_area': visible_area.to_list(), 'observer_height': terrain_height, 'target_height': target_height, 'max_distance_km': max_distance_km}

    def calculate_polygon_centroid(self, polygon: Polygon) -> Point:
        coords = polygon.coordinates
        n = len(coords)
        if n == 0:
            return Point(0.0, 0.0)
        avg_lng = sum(coord[0] for coord in coords) / n
        avg_lat = sum(coord[1] for coord in coords) / n
        return Point(avg_lng, avg_lat)

    def calculate_bounding_box(self, polygon: Polygon) -> Tuple[float, float, float, float]:
        coords = polygon.coordinates
        lngs = [coord[0] for coord in coords]
        lats = [coord[1] for coord in coords]
        return (min(lngs), min(lats), max(lngs), max(lats))

    def add_risk_entity(self, entity: SpatialRiskEntity):
        self.risk_entities.append(entity)

    def calculate_entity_risk(self, entity: SpatialRiskEntity, flight_plan: FlightPlan) -> SpatialRiskEntity:
        risk_score = 0.0
        entity_type_risk = {
            SpatialEntityType.NO_FLY_ZONE: 1.0,
            SpatialEntityType.TEMPORARY_RESTRICTION: 0.7,
            SpatialEntityType.AIRPORT_CLEARANCE: 0.8,
            SpatialEntityType.POPULATION_TARGET: 0.6,
            SpatialEntityType.SENSITIVE_TARGET: 0.7,
            SpatialEntityType.OBSTACLE: 0.5,
            SpatialEntityType.TERRAIN: 0.4,
            SpatialEntityType.WIND_FIELD: 0.3
        }
        base_risk = entity_type_risk.get(entity.entity_type, 0.5)
        entity_centroid = self.calculate_polygon_centroid(entity.geometry) if isinstance(entity.geometry, Polygon) else entity.geometry
        min_distance = float('inf')
        for waypoint in flight_plan.waypoints:
            distance = self.calculate_haversine_distance(entity_centroid, waypoint)
            min_distance = min(min_distance, distance)
        distance_factor = max(0.0, 1.0 - min_distance / 10.0)
        risk_score = base_risk * distance_factor
        if isinstance(entity.geometry, Polygon) and self.point_in_polygon_ray_casting(flight_plan.waypoints[0], entity.geometry):
            risk_score = max(risk_score, base_risk)
        entity.risk_score = risk_score
        entity.risk_level = RiskLevel.from_score(risk_score)
        return entity

    def assess_flight_plan_compliance(self, flight_plan: FlightPlan) -> Dict[str, Any]:
        compliance_issues = []
        total_risk_score = 0.0
        violated_rules = []
        for entity in self.risk_entities:
            updated_entity = self.calculate_entity_risk(entity, flight_plan)
            total_risk_score += updated_entity.risk_score
            for rule in self.compliance_rules:
                if self._check_rule_match(rule, updated_entity, flight_plan):
                    violated_rules.append({
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'rule_type': rule.rule_type,
                        'penalty': rule.penalty,
                        'reference': rule.reference,
                        'entity': updated_entity.name
                    })
                    total_risk_score += rule.penalty
                    compliance_issues.append({
                        'entity_id': updated_entity.id,
                        'entity_name': updated_entity.name,
                        'entity_type': updated_entity.entity_type.value,
                        'risk_score': updated_entity.risk_score,
                        'risk_level': updated_entity.risk_level.value,
                        'violated_rule': rule.name
                    })
        total_risk_score = min(1.0, total_risk_score)
        overall_risk_level = RiskLevel.from_score(total_risk_score)
        return {
            'flight_plan_id': flight_plan.id,
            'overall_risk_score': total_risk_score,
            'overall_risk_level': overall_risk_level.value,
            'is_compliant': overall_risk_level in [RiskLevel.SAFE, RiskLevel.LOW],
            'compliance_issues': compliance_issues,
            'violated_rules': violated_rules,
            'assessment_timestamp': None
        }

    def _check_rule_match(self, rule: ComplianceRule, entity: SpatialRiskEntity, flight_plan: FlightPlan) -> bool:
        conditions = rule.conditions
        if entity.entity_type.value != conditions.get('entity_type'):
            return False
        if 'distance_km' in conditions:
            entity_centroid = self.calculate_polygon_centroid(entity.geometry) if isinstance(entity.geometry, Polygon) else entity.geometry
            for waypoint in flight_plan.waypoints:
                distance = self.calculate_haversine_distance(entity_centroid, waypoint)
                if distance <= conditions['distance_km']:
                    return True
        if 'max_altitude' in conditions:
            if flight_plan.altitude > conditions['max_altitude']:
                entity_centroid = self.calculate_polygon_centroid(entity.geometry) if isinstance(entity.geometry, Polygon) else entity.geometry
                for waypoint in flight_plan.waypoints:
                    distance = self.calculate_haversine_distance(entity_centroid, waypoint)
                    if distance <= 5.0:
                        return True
        if 'safe_distance_km' in conditions:
            entity_centroid = self.calculate_polygon_centroid(entity.geometry) if isinstance(entity.geometry, Polygon) else entity.geometry
            for waypoint in flight_plan.waypoints:
                distance = self.calculate_haversine_distance(entity_centroid, waypoint)
                if distance <= conditions['safe_distance_km']:
                    return True
        if 'warning_distance_km' in conditions:
            entity_centroid = self.calculate_polygon_centroid(entity.geometry) if isinstance(entity.geometry, Polygon) else entity.geometry
            for waypoint in flight_plan.waypoints:
                distance = self.calculate_haversine_distance(entity_centroid, waypoint)
                if distance <= conditions['warning_distance_km']:
                    return True
        return False

    def generate_knowledge_graph_data(self) -> Dict[str, Any]:
        entities = []
        relations = []
        for entity in self.risk_entities:
            entities.append({
                'id': entity.id,
                'name': entity.name,
                'type': entity.entity_type.value,
                'properties': entity.properties
            })
        for rule in self.compliance_rules:
            entities.append({
                'id': rule.id,
                'name': rule.name,
                'type': 'compliance_rule',
                'properties': {'description': rule.description, 'rule_type': rule.rule_type, 'penalty': rule.penalty}
            })
        for rule in self.compliance_rules:
            for entity in self.risk_entities:
                if rule.conditions.get('entity_type') == entity.entity_type.value:
                    relations.append({
                        'source': rule.id,
                        'target': entity.id,
                        'type': '约束',
                        'properties': {'description': f'{rule.name} 适用于 {entity.name}'}
                    })
        for i, entity1 in enumerate(self.risk_entities):
            for j, entity2 in enumerate(self.risk_entities):
                if i >= j:
                    continue
                centroid1 = self.calculate_polygon_centroid(entity1.geometry) if isinstance(entity1.geometry, Polygon) else entity1.geometry
                centroid2 = self.calculate_polygon_centroid(entity2.geometry) if isinstance(entity2.geometry, Polygon) else entity2.geometry
                distance = self.calculate_haversine_distance(centroid1, centroid2)
                if distance <= 10.0:
                    relations.append({
                        'source': entity1.id,
                        'target': entity2.id,
                        'type': '邻近',
                        'properties': {'distance_km': round(distance, 2)}
                    })
        return {
            'entities': entities,
            'relations': relations,
            'metadata': {
                'entity_count': len(entities),
                'relation_count': len(relations),
                'model': 'spatial_risk_model'
            }
        }

_spatial_risk_model_instance = None

def get_spatial_risk_model() -> SpatialRiskModel:
    global _spatial_risk_model_instance
    if _spatial_risk_model_instance is None:
        _spatial_risk_model_instance = SpatialRiskModel()
    return _spatial_risk_model_instance
