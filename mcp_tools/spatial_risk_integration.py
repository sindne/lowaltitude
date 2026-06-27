import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools.spatial_risk_model import SpatialRiskModel, SpatialRiskEntity, SpatialEntityType, FlightPlan, ComplianceRule, RiskLevel, Point, Polygon
from mcp_tools.kg_rule_engine import KGRuleEngine, KGEntity, KGRelation, InferenceRule, RelationType, RuleType
from mcp_tools.enhanced_spatial_data import get_enhanced_spatial_data
from mcp_tools.sora_risk_assessment import SORARiskAssessor, DroneSpecs, GroundRiskData, AirRiskData, NaturalEnvironmentData, TopologyData, SAILLevel, AirRiskClass, WEIGHTS_DEFAULT, get_sora_assessor

class SpatialRiskIntegration:
    def __init__(self, amap_key: str = None, drone_specs: DroneSpecs = None):
        self.spatial_model = SpatialRiskModel()
        self.kg_engine = KGRuleEngine()
        self.enhanced_spatial_data = None
        self.amap_key = amap_key
        self._initialized = False
        self.sora_assessor = SORARiskAssessor(drone_specs)
        try:
            self.enhanced_spatial_data = get_enhanced_spatial_data(amap_key)
        except:
            pass

    def initialize(self, city_name: str, city_center: Tuple[float, float]):
        try:
            self._init_spatial_model(city_name, city_center)
            self._init_kg_engine()
            self._import_kg_data()
            self._initialized = True
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _init_spatial_model(self, city_name: str, city_center: Tuple[float, float]):
        lng, lat = city_center
        airport_point = Point(lng=lng + 0.05, lat=lat + 0.05)
        airport_buffer = self.spatial_model.buffer_point(airport_point, 5.0)
        self.spatial_model.risk_entities.append(SpatialRiskEntity(
            name=f'{city_name}天河机场禁飞区',
            entity_type=SpatialEntityType.NO_FLY_ZONE,
            geometry=airport_buffer,
            risk_score=1.0,
            risk_level=RiskLevel.CRITICAL,
            properties={'description': '机场核心禁飞区,半径5公里', 'regulation_reference': '《民用无人机空中交通管理规定》'}
        ))
        clearance_buffer = self.spatial_model.buffer_point(airport_point, 15.0)
        self.spatial_model.risk_entities.append(SpatialRiskEntity(
            name=f'{city_name}天河机场净空区',
            entity_type=SpatialEntityType.AIRPORT_CLEARANCE,
            geometry=clearance_buffer,
            risk_score=0.7,
            risk_level=RiskLevel.HIGH,
            properties={'description': '机场净空保护区,半径15公里', 'regulation_reference': '《民用机场飞行区技术标准》'}
        ))
        gov_point = Point(lng=lng, lat=lat)
        gov_buffer = self.spatial_model.buffer_point(gov_point, 1.0)
        self.spatial_model.risk_entities.append(SpatialRiskEntity(
            name=f'{city_name}市政府',
            entity_type=SpatialEntityType.SENSITIVE_TARGET,
            geometry=gov_buffer,
            risk_score=0.7,
            risk_level=RiskLevel.HIGH,
            properties={'description': '市级政府机关,敏感目标', 'regulation_reference': '《低空空域使用管理规定》'}
        ))
        pop_point = Point(lng=lng - 0.02, lat=lat - 0.03)
        pop_buffer = self.spatial_model.buffer_point(pop_point, 2.0)
        self.spatial_model.risk_entities.append(SpatialRiskEntity(
            name=f'{city_name}江汉路商圈',
            entity_type=SpatialEntityType.POPULATION_TARGET,
            geometry=pop_buffer,
            risk_score=0.6,
            risk_level=RiskLevel.HIGH,
            properties={'description': '市中心商业密集区,人口密度高', 'regulation_reference': '《城市低空航路划设指南》'}
        ))
        obs_point = Point(lng=lng + 0.03, lat=lat - 0.02)
        obs_buffer = self.spatial_model.buffer_point(obs_point, 0.5)
        self.spatial_model.risk_entities.append(SpatialRiskEntity(
            name=f'{city_name}绿地中心',
            entity_type=SpatialEntityType.OBSTACLE,
            geometry=obs_buffer,
            risk_score=0.4,
            risk_level=RiskLevel.MEDIUM,
            properties={'height': 475, 'description': '超高层建筑,高度475米', 'regulation_reference': '《低空空域风险评估规范》'}
        ))

    def _init_kg_engine(self):
        for entity in self.spatial_model.risk_entities:
            kg_entity = KGEntity(
                name=entity.name,
                entity_type=entity.entity_type.value,
                id=entity.id,
                properties=entity.properties
            )
            self.kg_engine.add_entity(kg_entity)
        for rule in self.spatial_model.compliance_rules:
            kg_rule = KGEntity(
                name=rule.name,
                entity_type='compliance_rule',
                id=rule.id,
                properties={
                    'description': rule.description,
                    'rule_type': rule.rule_type,
                    'penalty': rule.penalty,
                    'reference': rule.reference
                }
            )
            self.kg_engine.add_entity(kg_rule)

    def _import_kg_data(self):
        for rule in self.spatial_model.compliance_rules:
            for entity in self.spatial_model.risk_entities:
                if rule.conditions.get('entity_type') == entity.entity_type.value:
                    relation = KGRelation(
                        source_id=rule.id,
                        target_id=entity.id,
                        relation_type=RelationType.CONSTRAINTS,
                        properties={'description': f'{rule.name} 适用于 {entity.name}'}
                    )
                    self.kg_engine.add_relation(relation)
        print(f'[集成] 已导入 {len(self.kg_engine.entities)} 个实体和 {len(self.kg_engine.relations)} 个关系')

    def assess_risk(self, flight_plan_data: Dict[str, Any], city_name: str = None,
                   sora_ground_data: GroundRiskData = None, sora_air_data: AirRiskData = None,
                   sora_natural_data: NaturalEnvironmentData = None, sora_topology_data: TopologyData = None) -> Dict[str, Any]:
        try:
            waypoints_data = flight_plan_data.get('waypoints', [])
            waypoints = [Point(lng=w[1], lat=w[0]) for w in waypoints_data]
            flight_plan = FlightPlan(waypoints=waypoints, altitude=flight_plan_data.get('altitude', 100.0))
            spatial_result = self._assess_spatial(flight_plan)
            enhanced_result = None
            if self.enhanced_spatial_data:
                enhanced_result = self._assess_enhanced_spatial(waypoints_data, flight_plan.altitude, city_name)
            kg_result = self._run_kg_inference(flight_plan, spatial_result)
            integrated_result = self._integrate_results(spatial_result, kg_result, enhanced_result,
                                                       sora_ground_data, sora_air_data, sora_natural_data, sora_topology_data)
            return integrated_result
        except Exception as e:
            print(f'[集成] 风险评估失败: {e}')
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'overall_risk_score': 0.0, 'overall_risk_level': '未知'}

    def _assess_enhanced_spatial(self, waypoints_data: List[List[float]], flight_altitude: float, city_name: str = None) -> Dict[str, Any]:
        if not self.enhanced_spatial_data:
            return None
        all_assessments = []
        for waypoint in waypoints_data:
            lat, lng = waypoint
            assessment = self.enhanced_spatial_data.get_combined_risk_assessment(
                lng=lng, lat=lat, flight_altitude=flight_altitude, city_name=city_name
            )
            all_assessments.append(assessment)
        if not all_assessments:
            return None
        avg_risk = sum(a['overall_risk_score'] for a in all_assessments) / len(all_assessments)
        max_risk = max(a['overall_risk_score'] for a in all_assessments)
        dominant_factors = [a['dominant_risk_factor'] for a in all_assessments]
        if max_risk >= 0.7:
            overall_level = '极高'
        elif max_risk >= 0.5:
            overall_level = '高'
        elif max_risk >= 0.3:
            overall_level = '中等'
        else:
            overall_level = '低'
        return {
            'average_risk_score': round(avg_risk, 2),
            'max_risk_score': round(max_risk, 2),
            'overall_risk_level': overall_level,
            'dominant_factors': list(set(dominant_factors)),
            'waypoint_assessments': all_assessments
        }

    def _assess_spatial(self, flight_plan: FlightPlan) -> Dict[str, Any]:
        total_risk_score = 0.0
        compliance_issues = []
        for entity in self.spatial_model.risk_entities:
            for waypoint in flight_plan.waypoints:
                if hasattr(entity.geometry, 'lng'):
                    distance = self.spatial_model.calculate_haversine_distance(waypoint, entity.geometry)
                else:
                    distance = self.spatial_model.calculate_haversine_distance(waypoint, entity.geometry)
                compliance_issues.append({
                    'entity_name': entity.name,
                    'entity_type': entity.entity_type.value,
                    'risk_level': entity.risk_level.value,
                    'distance_km': round(distance, 2),
                    'description': f'距离 {entity.name} 仅 {distance:.2f} 公里'
                })
                total_risk_score = max(total_risk_score, entity.risk_score)
        risk_level = RiskLevel.from_score(total_risk_score)
        is_compliant = total_risk_score < 0.5
        return {
            'overall_risk_score': total_risk_score,
            'overall_risk_level': risk_level,
            'is_compliant': is_compliant,
            'compliance_issues': compliance_issues
        }

    def _run_kg_inference(self, flight_plan: FlightPlan, spatial_result: Dict) -> Dict:
        rule_applications = self.kg_engine.apply_rules()
        entities_to_check = [issue.get('entity_name', '') for issue in spatial_result.get('compliance_issues', [])]
        compliance_result = self.kg_engine.check_compliance(entities_to_check)
        return {
            'rule_applications': rule_applications,
            'compliance_check': compliance_result
        }

    def _integrate_results(self, spatial_result: Dict, kg_result: Dict, enhanced_result: Dict = None,
                          sora_ground_data: GroundRiskData = None, sora_air_data: AirRiskData = None,
                          sora_natural_data: NaturalEnvironmentData = None, sora_topology_data: TopologyData = None) -> Dict:
        spatial_score = spatial_result.get('overall_risk_score', 0.0)
        spatial_level = spatial_result.get('overall_risk_level', RiskLevel.SAFE).value
        compliance_check = kg_result.get('compliance_check', {})
        is_compliant = compliance_check.get('is_compliant', True)
        violations = compliance_check.get('violations', [])
        warnings = compliance_check.get('warnings', [])
        enhanced_score = 0.0
        enhanced_level = '安全'
        dominant_factors = []
        if enhanced_result:
            enhanced_score = enhanced_result.get('max_risk_score', 0.0)
            enhanced_level = enhanced_result.get('overall_risk_level', '安全')
            dominant_factors = enhanced_result.get('dominant_factors', [])
        violation_penalty = len(violations) * 0.15
        warning_penalty = len(warnings) * 0.1
        base_spatial_score = spatial_score * 0.35
        base_enhanced_score = enhanced_score * 0.4
        weighted_score = min(1.0, base_spatial_score + base_enhanced_score + violation_penalty + warning_penalty)
        sora_result = None
        if sora_ground_data or sora_air_data or sora_natural_data or sora_topology_data:
            try:
                sora_result = self.sora_assessor.assess(sora_ground_data, sora_air_data, sora_natural_data, sora_topology_data)
                print(f'[SORA] SAIL等级: {sora_result["sora_assessment"]["sail_level"]}, 地面风险等级: {sora_result["sora_assessment"]["ground_risk_level"]}, 空中风险等级: {sora_result["sora_assessment"]["air_risk_class"]}')
            except Exception as e:
                print(f'[SORA] SORA评估失败: {e}')
                sora_result = None
        if sora_result:
            sora_risk_score = sora_result['final_risk_score']
            sora_weight = 0.6
            weighted_weight = 0.4
            integrated_score = sora_risk_score * sora_weight + weighted_score * weighted_weight
            sora_risk_level = sora_result['risk_level']
        else:
            integrated_score = weighted_score
            sora_risk_level = None
        if sora_risk_level:
            integrated_level = sora_risk_level
        elif integrated_score >= 0.7:
            integrated_level = '极高风险'
        elif integrated_score >= 0.4:
            integrated_level = '高风险'
        elif integrated_score >= 0.2:
            integrated_level = '中等风险'
        else:
            integrated_level = '低风险'
        result = {
            'success': True,
            'overall_risk_score': round(integrated_score, 4),
            'overall_risk_level': integrated_level,
            'is_compliant': is_compliant and spatial_result.get('is_compliant', True),
            'weighted_validation_score': round(weighted_score, 4),
            'spatial_assessment': {
                'risk_score': round(spatial_score, 2),
                'risk_level': spatial_level,
                'compliance_issues': spatial_result.get('compliance_issues', [])
            },
            'knowledge_graph_assessment': {
                'violations': violations,
                'warnings': warnings,
                'rule_applications': kg_result.get('rule_applications', [])
            },
            'knowledge_graph_data': self.get_knowledge_graph_data()
        }
        if sora_result:
            result['sora_assessment'] = sora_result
        if enhanced_result:
            result['enhanced_spatial_assessment'] = enhanced_result
        return result

    def get_knowledge_graph_data(self) -> Dict[str, Any]:
        return self.spatial_model.generate_knowledge_graph_data()

    def get_spatial_entities(self) -> List[Dict[str, Any]]:
        entities = []
        for entity in self.spatial_model.risk_entities:
            entities.append(entity.to_dict())
        return entities

    def reset(self):
        self.spatial_model = SpatialRiskModel()
        self.kg_engine = KGRuleEngine()
        self._initialized = False

_spatial_risk_integration = None

def get_spatial_risk_integration(amap_key: str = None, drone_specs: DroneSpecs = None) -> SpatialRiskIntegration:
    global _spatial_risk_integration
    if _spatial_risk_integration is None:
        _spatial_risk_integration = SpatialRiskIntegration(amap_key, drone_specs)
    return _spatial_risk_integration
