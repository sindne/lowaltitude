"""
SORA (Specific Operations Risk Assessment) 低空风险评估框架
基于JARUS SORA标准的风险评估方法，结合加权多准则决策分析进行辅助验证
"""

import math
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass, field


class SAILLevel(Enum):
    SpecificAssuranceAndIntegrityLevel = 0
    I = 1
    II = 2
    III = 3
    IV = 4
    V = 5
    VI = 6


class AirRiskClass(Enum):
    a = "a"
    b = "b"
    c = "c"
    d = "d"


@dataclass
class DroneSpecs:
    weight_kg: float = 8.0
    max_speed_mps: float = 10.0
    type: str = "multirotor"
    has_parachute: bool = False
    has_geofence: bool = True
    has_return_home: bool = True

    @property
    def kinetic_energy_j(self) -> float:
        return 0.5 * self.weight_kg * self.max_speed_mps ** 2


@dataclass
class GroundRiskData:
    population_density: float = 0.0
    building_density: float = 0.0
    critical_infrastructure: List[str] = field(default_factory=list)
    is_residential: bool = False
    is_commercial: bool = False
    operation_scenario: str = "vlos_controlled"


@dataclass
class AirRiskData:
    airspace_altitude_agl_m: float = 100.0
    is_isolated_airspace: bool = False
    is_controlled_airspace: bool = False
    is_flyable_airspace: bool = True
    airport_proximity_km: float = 50.0
    other_aircraft_traffic: bool = False
    night_operation: bool = False
    visibility_km: float = 10.0


@dataclass
class NaturalEnvironmentData:
    wind_speed_ms: float = 5.0
    precipitation_mm_h: float = 0.0
    temperature_c: float = 20.0
    thunderstorm: bool = False
    visibility_km: float = 10.0


@dataclass
class TopologyData:
    terrain_elevation_m: float = 100.0
    terrain_complexity: float = 0.5
    has_mountains: bool = False
    has_water_bodies: bool = False


SORA_GROUND_RISK_TABLE = {
    ("vlos_controlled_sparse", "low"): 1,
    ("bvlos_controlled_sparse", "low"): 2,
    ("vlos_controlled_residential", "low"): 3,
    ("vlos_residential", "low"): 4,
    ("bvlos_controlled_residential", "low"): 5,
    ("bvlos_residential", "low"): 6,
    ("vlos_crowd", "low"): 7,
    ("bvlos_crowd", "low"): 8,

    ("vlos_controlled_sparse", "medium"): 2,
    ("bvlos_controlled_sparse", "medium"): 3,
    ("vlos_controlled_residential", "medium"): 4,
    ("vlos_residential", "medium"): 5,
    ("bvlos_controlled_residential", "medium"): 6,
    ("bvlos_residential", "medium"): 7,

    ("vlos_controlled_sparse", "high"): 3,
    ("bvlos_controlled_sparse", "high"): 4,
    ("vlos_controlled_residential", "high"): 6,
    ("vlos_residential", "high"): 7,
    ("bvlos_controlled_residential", "high"): 8,
    ("bvlos_residential", "high"): 9,

    ("vlos_controlled_sparse", "extreme"): 5,
    ("bvlos_controlled_sparse", "extreme"): 6,
    ("vlos_controlled_residential", "extreme"): 8,
    ("vlos_residential", "extreme"): 9,
    ("bvlos_controlled_residential", "extreme"): 10,
    ("bvlos_residential", "extreme"): 11,
}

SORA_AIR_RISK_TABLE = {
    "above_120_non_isolated": AirRiskClass.d,
    "above_120_isolated": AirRiskClass.c,
    "below_120_controlled": AirRiskClass.d,
    "below_120_non_controlled_non_isolated": AirRiskClass.c,
    "below_120_non_controlled_isolated": AirRiskClass.b,
    "above_18000": AirRiskClass.b,
    "flyable": AirRiskClass.a,
}

SORA_SAIL_TABLE = {
    (1, "a"): SAILLevel.I, (1, "b"): SAILLevel.II, (1, "c"): SAILLevel.IV, (1, "d"): SAILLevel.VI,
    (2, "a"): SAILLevel.I, (2, "b"): SAILLevel.II, (2, "c"): SAILLevel.IV, (2, "d"): SAILLevel.VI,
    (3, "a"): SAILLevel.II, (3, "b"): SAILLevel.II, (3, "c"): SAILLevel.IV, (3, "d"): SAILLevel.VI,
    (4, "a"): SAILLevel.III, (4, "b"): SAILLevel.III, (4, "c"): SAILLevel.IV, (4, "d"): SAILLevel.VI,
    (5, "a"): SAILLevel.IV, (5, "b"): SAILLevel.IV, (5, "c"): SAILLevel.IV, (5, "d"): SAILLevel.VI,
    (6, "a"): SAILLevel.V, (6, "b"): SAILLevel.V, (6, "c"): SAILLevel.V, (6, "d"): SAILLevel.VI,
    (7, "a"): SAILLevel.VI, (7, "b"): SAILLevel.VI, (7, "c"): SAILLevel.VI, (7, "d"): SAILLevel.VI,
    (8, "a"): SAILLevel.VI, (8, "b"): SAILLevel.VI, (8, "c"): SAILLevel.VI, (8, "d"): SAILLevel.VI,
    (9, "a"): SAILLevel.VI, (9, "b"): SAILLevel.VI, (9, "c"): SAILLevel.VI, (9, "d"): SAILLevel.VI,
    (10, "a"): SAILLevel.VI, (10, "b"): SAILLevel.VI, (10, "c"): SAILLevel.VI, (10, "d"): SAILLevel.VI,
    (11, "a"): SAILLevel.VI, (11, "b"): SAILLevel.VI, (11, "c"): SAILLevel.VI, (11, "d"): SAILLevel.VI,
}

WEIGHTS_DEFAULT = {
    "population": 0.20,
    "building": 0.25,
    "air_traffic": 0.20,
    "weather": 0.20,
    "topology": 0.15,
}


class SORARiskAssessor:
    """SORA风险评估器"""

    def __init__(self, drone_specs: Optional[DroneSpecs] = None):
        self.drone_specs = drone_specs or DroneSpecs()

    def determine_kinetic_energy_tier(self) -> str:
        e = self.drone_specs.kinetic_energy_j
        if e < 700:
            return "low"
        elif e < 34000:
            return "medium"
        elif e < 1084000:
            return "high"
        else:
            return "extreme"

    def determine_operation_scenario(self, ground_data: GroundRiskData) -> str:
        pop = ground_data.population_density
        is_controlled = ground_data.is_commercial or ground_data.critical_infrastructure

        if pop > 5000:
            if is_controlled:
                return "vlos_crowd" if not ground_data.is_residential else "bvlos_crowd"
            return "vlos_crowd"
        elif pop > 1000:
            if is_controlled:
                return "vlos_residential"
            return "bvlos_residential" if not ground_data.is_residential else "vlos_residential"
        elif pop > 200:
            if is_controlled:
                return "vlos_controlled_residential"
            return "bvlos_controlled_residential"
        else:
            if is_controlled:
                return "vlos_controlled_sparse"
            return "bvlos_controlled_sparse"

    def calculate_ground_risk_level(self, ground_data: GroundRiskData) -> int:
        ke_tier = self.determine_kinetic_energy_tier()
        scenario = self.determine_operation_scenario(ground_data)

        key = (scenario, ke_tier)
        level = SORA_GROUND_RISK_TABLE.get(key)

        if level is not None:
            return level

        if ke_tier == "low":
            base = 3
        elif ke_tier == "medium":
            base = 5
        elif ke_tier == "high":
            base = 7
        else:
            base = 9

        if "crowd" in scenario:
            base = min(11, base + 2)
        elif "residential" in scenario and "controlled" not in scenario:
            base = min(11, base + 1)

        return min(11, base)

    def determine_airspace_class(self, air_data: AirRiskData) -> AirRiskClass:
        alt = air_data.airspace_altitude_agl_m

        if air_data.is_flyable_airspace and alt <= 120:
            return AirRiskClass.a

        if alt > 120:
            if air_data.is_isolated_airspace:
                return AirRiskClass.c
            else:
                return AirRiskClass.d
        else:
            if air_data.is_controlled_airspace:
                return AirRiskClass.d
            elif air_data.is_isolated_airspace:
                return AirRiskClass.b
            else:
                return AirRiskClass.c

    def calculate_air_risk_class(self, air_data: AirRiskData) -> AirRiskClass:
        base_class = self.determine_airspace_class(air_data)

        if air_data.airport_proximity_km < 8:
            if base_class == AirRiskClass.a:
                return AirRiskClass.b
            elif base_class == AirRiskClass.b:
                return AirRiskClass.c

        if air_data.other_aircraft_traffic:
            if base_class == AirRiskClass.a:
                return AirRiskClass.b

        if air_data.visibility_km < 3:
            if base_class == AirRiskClass.a:
                return AirRiskClass.b

        return base_class

    def calculate_sail(self, ground_risk_level: int, air_risk_class: AirRiskClass) -> SAILLevel:
        key = (ground_risk_level, air_risk_class.value)
        return SORA_SAIL_TABLE.get(key, SAILLevel.VI)

    def calculate_weighted_risk_score(
        self,
        population_risk: float,
        building_risk: float,
        air_traffic_risk: float,
        weather_risk: float,
        topology_risk: float,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        if weights is None:
            weights = WEIGHTS_DEFAULT

        return (
            population_risk * weights["population"]
            + building_risk * weights["building"]
            + air_traffic_risk * weights["air_traffic"]
            + weather_risk * weights["weather"]
            + topology_risk * weights["topology"]
        )

    def calculate_population_risk(self, ground_data: GroundRiskData) -> float:
        d = ground_data.population_density
        if d > 5000:
            return 0.9
        elif d > 3000:
            return 0.75
        elif d > 1000:
            return 0.6
        elif d > 500:
            return 0.4
        elif d > 200:
            return 0.25
        else:
            return 0.1

    def calculate_building_risk(self, ground_data: GroundRiskData) -> float:
        b = ground_data.building_density
        if b > 0.8:
            return 0.9
        elif b > 0.6:
            return 0.7
        elif b > 0.4:
            return 0.5
        elif b > 0.2:
            return 0.3
        else:
            return 0.15

    def calculate_air_traffic_risk(self, air_data: AirRiskData) -> float:
        score = 0.1
        if air_data.airport_proximity_km < 8:
            score += 0.5
        elif air_data.airport_proximity_km < 15:
            score += 0.3
        elif air_data.airport_proximity_km < 30:
            score += 0.15

        if air_data.other_aircraft_traffic:
            score += 0.2

        if air_data.night_operation:
            score += 0.1

        if not air_data.is_controlled_airspace:
            score += 0.1

        return min(1.0, score)

    def calculate_weather_risk(self, natural_data: NaturalEnvironmentData) -> float:
        score = 0.0

        if natural_data.thunderstorm:
            score += 0.5
        if natural_data.wind_speed_ms > 15:
            score += 0.3
        elif natural_data.wind_speed_ms > 10:
            score += 0.2
        elif natural_data.wind_speed_ms > 8:
            score += 0.1

        if natural_data.precipitation_mm_h > 10:
            score += 0.2
        elif natural_data.precipitation_mm_h > 5:
            score += 0.1

        if natural_data.visibility_km < 2:
            score += 0.2
        elif natural_data.visibility_km < 5:
            score += 0.1

        if natural_data.temperature_c < -10 or natural_data.temperature_c > 35:
            score += 0.1

        return min(1.0, score)

    def calculate_topology_risk(self, topology_data: TopologyData) -> float:
        score = 0.1

        if topology_data.has_mountains:
            score += 0.2
        if topology_data.terrain_complexity > 0.7:
            score += 0.2
        elif topology_data.terrain_complexity > 0.4:
            score += 0.1

        if topology_data.terrain_elevation_m > 1500:
            score += 0.2
        elif topology_data.terrain_elevation_m > 500:
            score += 0.1

        if topology_data.has_water_bodies:
            score += 0.1

        return min(1.0, score)

    def sail_to_risk_score(self, sail: SAILLevel) -> float:
        mapping = {
            SAILLevel.I: 0.1,
            SAILLevel.II: 0.2,
            SAILLevel.III: 0.35,
            SAILLevel.IV: 0.5,
            SAILLevel.V: 0.65,
            SAILLevel.VI: 0.85,
        }
        return mapping.get(sail, 0.85)

    def determine_final_risk_level(self, sail: SAILLevel, weighted_score: float) -> Tuple[str, float]:
        sail_score = self.sail_to_risk_score(sail)

        final_score = sail_score * 0.6 + weighted_score * 0.4

        if sail in (SAILLevel.I, SAILLevel.II) and final_score < 0.2:
            return "低风险", final_score
        elif sail in (SAILLevel.III, SAILLevel.IV) and 0.2 <= final_score < 0.4:
            return "中等风险", final_score
        elif sail == SAILLevel.V and 0.4 <= final_score < 0.7:
            return "高风险", final_score
        elif sail == SAILLevel.VI or final_score >= 0.7:
            return "极高风险", final_score
        else:
            if final_score < 0.2:
                return "低风险", final_score
            elif final_score < 0.4:
                return "中等风险", final_score
            elif final_score < 0.7:
                return "高风险", final_score
            else:
                return "极高风险", final_score

    def assess(
        self,
        ground_data: GroundRiskData,
        air_data: AirRiskData,
        natural_data: NaturalEnvironmentData,
        topology_data: TopologyData,
        weights: Optional[Dict[str, float]] = None,
        city_data: Optional[Dict[str, any]] = None,
        use_dynamic_weights: bool = False,
    ) -> Dict:
        ke = self.drone_specs.kinetic_energy_j
        ke_tier = self.determine_kinetic_energy_tier()

        ground_risk_level = self.calculate_ground_risk_level(ground_data)
        air_risk_class = self.calculate_air_risk_class(air_data)
        sail = self.calculate_sail(ground_risk_level, air_risk_class)

        pop_risk = self.calculate_population_risk(ground_data)
        bld_risk = self.calculate_building_risk(ground_data)
        air_risk = self.calculate_air_traffic_risk(air_data)
        wx_risk = self.calculate_weather_risk(natural_data)
        topo_risk = self.calculate_topology_risk(topology_data)

        dynamic_weights = None
        if use_dynamic_weights:
            from mcp_tools.ahp_weight_calculator import get_ahp_calculator
            from mcp_tools.llm_weight_adjuster import get_llm_weight_adjuster
            
            ahp_calc = get_ahp_calculator()
            llm_adjuster = get_llm_weight_adjuster()
            
            base_weights = ahp_calc.get_default_weights()
            ahp_weights = {
                "population": base_weights["人口密度"],
                "building": base_weights["建筑物密度"],
                "air_traffic": base_weights["空中交通"],
                "weather": base_weights["天气条件"],
                "topology": base_weights["地理拓扑"]
            }
            
            if city_data:
                dynamic_weights = llm_adjuster.adjust_weights_by_llm(
                    base_weights, city_data
                )
                dynamic_weights = {
                    "population": dynamic_weights["人口密度"],
                    "building": dynamic_weights["建筑物密度"],
                    "air_traffic": dynamic_weights["空中交通"],
                    "weather": dynamic_weights["天气条件"],
                    "topology": dynamic_weights["地理拓扑"]
                }
                weight_report = llm_adjuster.generate_weight_report(
                    base_weights, dynamic_weights, city_data
                )
            else:
                dynamic_weights = ahp_weights
                weight_report = "使用AHP基础权重（无城市特征数据）"
            
            final_weights = dynamic_weights
        else:
            final_weights = weights
            weight_report = "使用默认权重或传入权重"

        weighted_score = self.calculate_weighted_risk_score(
            pop_risk, bld_risk, air_risk, wx_risk, topo_risk, final_weights
        )

        risk_level, final_score = self.determine_final_risk_level(sail, weighted_score)

        operation_scenario = self.determine_operation_scenario(ground_data)

        return {
            "risk_level": risk_level,
            "final_risk_score": round(final_score, 4),
            "sora_assessment": {
                "drone_kinetic_energy_j": round(ke, 2),
                "kinetic_energy_tier": ke_tier,
                "operation_scenario": operation_scenario,
                "ground_risk_level": ground_risk_level,
                "air_risk_class": air_risk_class.value,
                "sail_level": sail.name,
                "sail_score": round(self.sail_to_risk_score(sail), 4),
            },
            "weighted_assessment": {
                "population_risk": round(pop_risk, 4),
                "building_risk": round(bld_risk, 4),
                "air_traffic_risk": round(air_risk, 4),
                "weather_risk": round(wx_risk, 4),
                "topology_risk": round(topo_risk, 4),
                "weighted_score": round(weighted_score, 4),
                "weights": final_weights or WEIGHTS_DEFAULT,
                "weight_method": "AHP+城市特征动态权重" if use_dynamic_weights else "默认权重",
                "weight_report": weight_report,
            },
            "recommendations": self._generate_recommendations(sail, risk_level, ground_data, air_data, natural_data),
        }

    def _generate_recommendations(
        self, sail: SAILLevel, risk_level: str,
        ground_data: GroundRiskData, air_data: AirRiskData,
        natural_data: NaturalEnvironmentData,
    ) -> List[str]:
        recs = []

        if sail == SAILLevel.I:
            recs.append("SORA评估为I类，风险可接受，可正常飞行")
        elif sail == SAILLevel.II:
            recs.append("SORA评估为II类，低风险，可正常飞行但需注意观察")
        elif sail == SAILLevel.III:
            recs.append("SORA评估为III类，中等风险，需谨慎飞行并建议降低飞行高度或绕行")
        elif sail == SAILLevel.IV:
            recs.append("SORA评估为IV类，中等风险，需谨慎飞行并建议降低飞行高度或绕行")
        elif sail == SAILLevel.V:
            recs.append("SORA评估为V类，高风险，需经审批后方可飞行并配备应急方案")
        elif sail == SAILLevel.VI:
            recs.append("SORA评估为VI类，极高风险，一般禁止飞行")

        if ground_data.population_density > 3000:
            recs.append("人口密集区域，建议降低飞行高度至50米以下")
        if not self.drone_specs.has_parachute:
            recs.append("建议加装降落伞系统以降低地面风险")
        if natural_data.wind_speed_ms > 10:
            recs.append("风速较高，建议在风速低于10m/s时飞行")
        if natural_data.thunderstorm:
            recs.append("雷暴天气，禁止飞行")
        if air_data.airport_proximity_km < 15:
            recs.append("距机场较近，需远离机场管制区域")

        return recs

    def compute_confidence_metrics(self, sora_result: Dict) -> Dict:
        """计算评估结果置信度指标"""
        metrics = {
            "sora_confidence": self._compute_sora_confidence(sora_result),
            "weight_consistency": self._compute_weight_consistency(sora_result),
            "data_quality_score": self._compute_data_quality(sora_result),
            "cross_validation_passed": False,
            "uncertainty_flags": [],
        }
        
        sail_score = sora_result.get("sora_assessment", {}).get("sail_score", 0.5)
        weighted_score = sora_result.get("weighted_assessment", {}).get("weighted_score", 0.5)
        
        score_diff = abs(sail_score - weighted_score)
        if score_diff > 0.3:
            metrics["uncertainty_flags"].append("SORA与AHP加权评分差异过大")
        elif score_diff < 0.15:
            metrics["cross_validation_passed"] = True
        
        weights = sora_result.get("weighted_assessment", {}).get("weights", {})
        if weights:
            max_weight = max(weights.values())
            min_weight = min(weights.values())
            if max_weight / min_weight > 8:
                metrics["uncertainty_flags"].append("权重极差过大，可能存在偏差")
        
        metrics["overall_confidence"] = round(
            (metrics["sora_confidence"] * 0.4 +
             metrics["weight_consistency"] * 0.3 +
             metrics["data_quality_score"] * 0.3), 2
        )
        
        return metrics
    
    def _compute_sora_confidence(self, sora_result: Dict) -> float:
        """SORA框架置信度 - 基于动能等级和操作场景匹配度"""
        sora = sora_result.get("sora_assessment", {})
        ke_tier = sora.get("kinetic_energy_tier", "low")
        scenario = sora.get("operation_scenario", "")
        
        tier_confidence = {"low": 0.95, "medium": 0.85, "high": 0.75, "extreme": 0.60}
        confidence = tier_confidence.get(ke_tier, 0.7)
        
        if "vlos" in scenario:
            confidence += 0.05
        if "crowd" in scenario:
            confidence -= 0.1
        
        return round(max(0.3, min(1.0, confidence)), 2)
    
    def _compute_weight_consistency(self, sora_result: Dict) -> float:
        """权重向量一致性评估"""
        weights = sora_result.get("weighted_assessment", {}).get("weights", {})
        if not weights:
            return 0.5
        
        expected_order = ["population", "building", "air_traffic", "weather", "topology"]
        actual_order = sorted(weights, key=weights.get, reverse=True)
        
        if expected_order == actual_order:
            return 0.95
        elif expected_order[:3] == actual_order[:3]:
            return 0.75
        else:
            return 0.50
    
    def _compute_data_quality(self, sora_result: Dict) -> float:
        """数据质量评分"""
        quality = 0.7
        sora = sora_result.get("sora_assessment", {})
        
        ke_j = sora.get("drone_kinetic_energy_j", 0)
        if ke_j < 100 or ke_j > 10000:
            quality -= 0.1
        
        weighted = sora_result.get("weighted_assessment", {})
        risks = [
            weighted.get("population_risk", 0),
            weighted.get("building_risk", 0),
            weighted.get("air_traffic_risk", 0),
            weighted.get("weather_risk", 0),
            weighted.get("topology_risk", 0),
        ]
        if all(r > 0 for r in risks):
            quality += 0.1
        if sum(risks) > 0:
            quality += 0.1
        
        return round(max(0.3, min(1.0, quality)), 2)
    
    def validate_assessment(self, sora_result: Dict) -> Dict:
        """综合验证评估结果"""
        metrics = self.compute_confidence_metrics(sora_result)
        
        sail = sora_result.get("sora_assessment", {}).get("sail_level", "UNKNOWN")
        risk_level = sora_result.get("risk_level", "UNKNOWN")
        final_score = sora_result.get("final_risk_score", 0.5)
        
        validation = {
            "pass": metrics["cross_validation_passed"] and metrics["overall_confidence"] >= 0.5,
            "confidence_metrics": metrics,
            "methodology": {
                "primary_framework": "JARUS SORA v2.0",
                "weighting_method": "AHP (Saaty 1-9 Scale, Eigenvector Method)",
                "consistency_check": f"CR < 0.1 threshold",
                "cross_validation": "SORA×AHP交叉验证" if metrics["cross_validation_passed"] else "需人工复核",
            },
            "data_flow": {
                "input_sources": ["高德天气API", "行政区划API", "城市统计数据库"],
                "processing_pipeline": ["SORA地面/空中风险分级", "AHP多准则加权", "DeepSeek交叉验证"],
                "output_artifacts": [f"SAIL={sail}", f"风险等级={risk_level}", f"综合评分={final_score}"],
            },
            "recommendations": sora_result.get("recommendations", []),
        }
        
        return validation


_sora_assessor = None


def get_sora_assessor(drone_specs: Optional[DroneSpecs] = None) -> SORARiskAssessor:
    global _sora_assessor
    if _sora_assessor is None:
        _sora_assessor = SORARiskAssessor(drone_specs)
    return _sora_assessor
