import sys
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
@dataclass
class RuleResult:
    rule_name: str
    risk_level: str  # 低、中、高
    risk_score: float  # 0-1
    details: str
    weight: float
class RuleBasedRiskAssessment:
    def __init__(self):
        self.rules = self._initialize_rules()
        self.rule_weights = {
            '空域分类规则': 0.15,
            '人口密度规则': 0.12,
            '建筑物高度规则': 0.10,
            '气象条件规则': 0.08,
            '机场距离规则': 0.15,
            '敏感区域规则': 0.12,
            '地形复杂度规则': 0.08,
            '电磁环境规则': 0.08,
            '飞行高度规则': 0.07,
            '飞行时间规则': 0.05
        }
    def _initialize_rules(self) -> Dict[str, callable]:
        return {
            '空域分类规则': self._rule_airspace_classification,
            '人口密度规则': self._rule_population_density,
            '建筑物高度规则': self._rule_building_height,
            '气象条件规则': self._rule_weather_conditions,
            '机场距离规则': self._rule_airport_distance,
            '敏感区域规则': self._rule_sensitive_areas,
            '地形复杂度规则': self._rule_terrain_complexity,
            '电磁环境规则': self._rule_electromagnetic_environment,
            '飞行高度规则': self._rule_flight_altitude,
            '飞行时间规则': self._rule_flight_time
        }
    def _rule_airspace_classification(self, params: Dict[str, Any]) -> RuleResult:
        airspace_type = params.get('airspace_type', 'C')  # A, B, C, D
        if airspace_type == 'A':
            return RuleResult('空域分类规则', '高', 0.9, '管制空域，禁止飞行', self.rule_weights['空域分类规则'])
        elif airspace_type == 'B':
            return RuleResult('空域分类规则', '中高', 0.7, '报告空域，需审批', self.rule_weights['空域分类规则'])
        elif airspace_type == 'C':
            return RuleResult('空域分类规则', '中', 0.5, '监视空域，需报备', self.rule_weights['空域分类规则'])
        else:
            return RuleResult('空域分类规则', '低', 0.3, '适飞空域，可自由飞行', self.rule_weights['空域分类规则'])
    def _rule_population_density(self, params: Dict[str, Any]) -> RuleResult:
        population_density = params.get('population_density', 2000)  # 人/km²
        if population_density > 10000:
            return RuleResult('人口密度规则', '极高', 0.95, f'人口密度极高：{population_density}人/km²', self.rule_weights['人口密度规则'])
        elif population_density > 5000:
            return RuleResult('人口密度规则', '高', 0.8, f'人口密度高：{population_density}人/km²', self.rule_weights['人口密度规则'])
        elif population_density > 1000:
            return RuleResult('人口密度规则', '中', 0.5, f'人口密度中等：{population_density}人/km²', self.rule_weights['人口密度规则'])
        else:
            return RuleResult('人口密度规则', '低', 0.2, f'人口密度低：{population_density}人/km²', self.rule_weights['人口密度规则'])
    def _rule_building_height(self, params: Dict[str, Any]) -> RuleResult:
        max_building_height = params.get('max_building_height', 30)  # 米
        if max_building_height > 100:
            return RuleResult('建筑物高度规则', '极高', 0.9, f'建筑物极高：{max_building_height}m', self.rule_weights['建筑物高度规则'])
        elif max_building_height > 50:
            return RuleResult('建筑物高度规则', '高', 0.75, f'建筑物较高：{max_building_height}m', self.rule_weights['建筑物高度规则'])
        elif max_building_height > 20:
            return RuleResult('建筑物高度规则', '中', 0.5, f'建筑物高度一般：{max_building_height}m', self.rule_weights['建筑物高度规则'])
        else:
            return RuleResult('建筑物高度规则', '低', 0.25, f'建筑物较矮：{max_building_height}m', self.rule_weights['建筑物高度规则'])
    def _rule_weather_conditions(self, params: Dict[str, Any]) -> RuleResult:
        wind_speed = params.get('wind_speed', 5)  # m/s
        visibility = params.get('visibility', 5)  # km
        precipitation = params.get('precipitation', 'none')  # none, light, moderate, heavy
        if wind_speed > 15 or visibility < 1 or precipitation == 'heavy':
            return RuleResult('气象条件规则', '极高', 0.95, f'恶劣天气：风速{wind_speed}m/s，能见度{visibility}km', self.rule_weights['气象条件规则'])
        elif wind_speed > 10 or visibility < 3 or precipitation == 'moderate':
            return RuleResult('气象条件规则', '高', 0.75, f'天气较差：风速{wind_speed}m/s，能见度{visibility}km', self.rule_weights['气象条件规则'])
        elif wind_speed > 5 or visibility < 5 or precipitation == 'light':
            return RuleResult('气象条件规则', '中', 0.5, f'天气一般：风速{wind_speed}m/s，能见度{visibility}km', self.rule_weights['气象条件规则'])
        else:
            return RuleResult('气象条件规则', '低', 0.2, f'天气良好：风速{wind_speed}m/s，能见度{visibility}km', self.rule_weights['气象条件规则'])
    def _rule_airport_distance(self, params: Dict[str, Any]) -> RuleResult:
        airport_distance = params.get('airport_distance', 15)  # km
        if airport_distance < 5:
            return RuleResult('机场距离规则', '极高', 0.95, f'距机场过近：{airport_distance}km', self.rule_weights['机场距离规则'])
        elif airport_distance < 10:
            return RuleResult('机场距离规则', '高', 0.8, f'距机场较近：{airport_distance}km', self.rule_weights['机场距离规则'])
        elif airport_distance < 20:
            return RuleResult('机场距离规则', '中', 0.5, f'距机场一般：{airport_distance}km', self.rule_weights['机场距离规则'])
        else:
            return RuleResult('机场距离规则', '低', 0.2, f'距机场较远：{airport_distance}km', self.rule_weights['机场距离规则'])
    def _rule_sensitive_areas(self, params: Dict[str, Any]) -> RuleResult:
        sensitive_areas = params.get('sensitive_areas', [])
        high_risk_areas = ['军事设施', '政府机关', '核电站']
        medium_risk_areas = ['学校', '医院', '监狱']
        low_risk_areas = ['商业区', '居民区', '公园']
        has_high = any(area in high_risk_areas for area in sensitive_areas)
        has_medium = any(area in medium_risk_areas for area in sensitive_areas)
        has_low = any(area in low_risk_areas for area in sensitive_areas)
        if has_high:
            return RuleResult('敏感区域规则', '极高', 0.9, f'存在高风险敏感区域：{sensitive_areas}', self.rule_weights['敏感区域规则'])
        elif has_medium:
            return RuleResult('敏感区域规则', '高', 0.7, f'存在中风险敏感区域：{sensitive_areas}', self.rule_weights['敏感区域规则'])
        elif has_low:
            return RuleResult('敏感区域规则', '中', 0.5, f'存在低风险敏感区域：{sensitive_areas}', self.rule_weights['敏感区域规则'])
        else:
            return RuleResult('敏感区域规则', '低', 0.2, '无明显敏感区域', self.rule_weights['敏感区域规则'])
    def _rule_terrain_complexity(self, params: Dict[str, Any]) -> RuleResult:
        terrain_type = params.get('terrain_type', '平原')  # 山地, 丘陵, 平原, 水域
        if terrain_type in ['山地', '峡谷']:
            return RuleResult('地形复杂度规则', '极高', 0.85, f'地形复杂：{terrain_type}', self.rule_weights['地形复杂度规则'])
        elif terrain_type == '丘陵':
            return RuleResult('地形复杂度规则', '高', 0.65, f'地形较复杂：{terrain_type}', self.rule_weights['地形复杂度规则'])
        elif terrain_type == '水域':
            return RuleResult('地形复杂度规则', '中', 0.45, f'地形一般：{terrain_type}', self.rule_weights['地形复杂度规则'])
        else:
            return RuleResult('地形复杂度规则', '低', 0.25, f'地形平坦：{terrain_type}', self.rule_weights['地形复杂度规则'])
    def _rule_electromagnetic_environment(self, params: Dict[str, Any]) -> RuleResult:
        em_interference = params.get('em_interference', '弱')  # 强, 中, 弱, 无
        if em_interference == '强':
            return RuleResult('电磁环境规则', '极高', 0.9, f'电磁干扰强', self.rule_weights['电磁环境规则'])
        elif em_interference == '中':
            return RuleResult('电磁环境规则', '高', 0.7, f'电磁干扰中等', self.rule_weights['电磁环境规则'])
        elif em_interference == '弱':
            return RuleResult('电磁环境规则', '中', 0.4, f'电磁干扰弱', self.rule_weights['电磁环境规则'])
        else:
            return RuleResult('电磁环境规则', '低', 0.2, f'无明显电磁干扰', self.rule_weights['电磁环境规则'])
    def _rule_flight_altitude(self, params: Dict[str, Any]) -> RuleResult:
        flight_altitude = params.get('flight_altitude', 50)  # 米
        if flight_altitude > 120:
            return RuleResult('飞行高度规则', '高', 0.8, f'飞行高度超限：{flight_altitude}m', self.rule_weights['飞行高度规则'])
        elif flight_altitude > 50:
            return RuleResult('飞行高度规则', '中', 0.5, f'飞行高度较高：{flight_altitude}m', self.rule_weights['飞行高度规则'])
        elif flight_altitude > 20:
            return RuleResult('飞行高度规则', '低', 0.3, f'飞行高度适中：{flight_altitude}m', self.rule_weights['飞行高度规则'])
        else:
            return RuleResult('飞行高度规则', '极低', 0.15, f'飞行高度低：{flight_altitude}m', self.rule_weights['飞行高度规则'])
    def _rule_flight_time(self, params: Dict[str, Any]) -> RuleResult:
        flight_time = params.get('flight_time', 12)  # 小时 (0-23)
        if flight_time >= 20 or flight_time < 6:
            return RuleResult('飞行时间规则', '高', 0.75, f'夜间飞行：{flight_time}:00', self.rule_weights['飞行时间规则'])
        elif (6 <= flight_time < 8) or (18 <= flight_time < 20):
            return RuleResult('飞行时间规则', '中', 0.5, f'傍晚/清晨飞行：{flight_time}:00', self.rule_weights['飞行时间规则'])
        else:
            return RuleResult('飞行时间规则', '低', 0.25, f'白天飞行：{flight_time}:00', self.rule_weights['飞行时间规则'])
    def assess(self, params: Dict[str, Any]) -> Dict[str, Any]:
        results = []
        total_score = 0
        total_weight = 0
        for rule_name, rule_func in self.rules.items():
            result = rule_func(params)
            results.append(result)
            total_score += result.risk_score * result.weight
            total_weight += result.weight
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0.5
        if final_score >= 0.8:
            risk_level = '极高'
        elif final_score >= 0.6:
            risk_level = '高'
        elif final_score >= 0.4:
            risk_level = '中'
        elif final_score >= 0.2:
            risk_level = '低'
        else:
            risk_level = '极低'
        return {
            'method': 'rule_based',
            'region': params.get('region', '未知地区'),
            'risk_score': final_score,
            'risk_level': risk_level,
            'rule_results': [
                {
                    'rule_name': r.rule_name,
                    'risk_level': r.risk_level,
                    'risk_score': r.risk_score,
                    'details': r.details,
                    'weight': r.weight
                }
                for r in results
            ],
            'total_weight': total_weight,
            'recommendations': self._generate_recommendations(results, final_score)
        }
    def _generate_recommendations(self, results: List[RuleResult], final_score: float) -> List[str]:
        recommendations = []
        high_risk_rules = [r for r in results if r.risk_score >= 0.7]
        for rule in high_risk_rules:
            if rule.rule_name == '空域分类规则':
                recommendations.append('建议申请空域使用许可，遵守管制空域飞行规定')
            elif rule.rule_name == '人口密度规则':
                recommendations.append('避开人口密集区域，选择开阔地带飞行')
            elif rule.rule_name == '建筑物高度规则':
                recommendations.append('保持足够安全高度，避免靠近高层建筑')
            elif rule.rule_name == '气象条件规则':
                recommendations.append('等待气象条件改善后再执行飞行任务')
            elif rule.rule_name == '机场距离规则':
                recommendations.append('远离机场净空保护区，遵守机场管理规定')
            elif rule.rule_name == '敏感区域规则':
                recommendations.append('避开军事设施、政府机关等敏感区域')
            elif rule.rule_name == '地形复杂度规则':
                recommendations.append('选择地形平坦区域飞行，避开复杂地形')
            elif rule.rule_name == '电磁环境规则':
                recommendations.append('避开强电磁干扰区域，确保通信畅通')
            elif rule.rule_name == '飞行高度规则':
                recommendations.append('遵守120m飞行高度限制，保持安全高度')
            elif rule.rule_name == '飞行时间规则':
                recommendations.append('选择白天时段飞行，避免夜间作业')
        if final_score >= 0.6:
            recommendations.append('综合风险较高，建议重新评估飞行计划')
        if not recommendations:
            recommendations.append('当前条件适合飞行，请遵守相关法规')
        return recommendations
CITY_FEATURES = {
    '深圳市': {
        'airspace_type': 'B',
        'population_density': 8800,
        'max_building_height': 592,
        'wind_speed': 3.5,
        'visibility': 8,
        'precipitation': 'none',
        'airport_distance': 8,
        'sensitive_areas': ['学校', '医院', '政府机关', '军事设施'],
        'terrain_type': '平原',
        'em_interference': '中',
        'flight_altitude': 80,
        'flight_time': 14
    },
    '广州市': {
        'airspace_type': 'B',
        'population_density': 6500,
        'max_building_height': 530,
        'wind_speed': 3.2,
        'visibility': 7,
        'precipitation': 'light',
        'airport_distance': 12,
        'sensitive_areas': ['学校', '医院', '商业区'],
        'terrain_type': '平原',
        'em_interference': '中',
        'flight_altitude': 70,
        'flight_time': 15
    },
    '上海市': {
        'airspace_type': 'B',
        'population_density': 9200,
        'max_building_height': 632,
        'wind_speed': 4.0,
        'visibility': 6,
        'precipitation': 'light',
        'airport_distance': 15,
        'sensitive_areas': ['学校', '医院', '政府机关', '商业区'],
        'terrain_type': '平原',
        'em_interference': '强',
        'flight_altitude': 90,
        'flight_time': 13
    },
    '北京市': {
        'airspace_type': 'A',
        'population_density': 7800,
        'max_building_height': 528,
        'wind_speed': 4.5,
        'visibility': 5,
        'precipitation': 'none',
        'airport_distance': 10,
        'sensitive_areas': ['军事设施', '政府机关', '学校', '医院'],
        'terrain_type': '平原',
        'em_interference': '强',
        'flight_altitude': 85,
        'flight_time': 14
    },
    '成都市': {
        'airspace_type': 'C',
        'population_density': 5200,
        'max_building_height': 468,
        'wind_speed': 2.5,
        'visibility': 8,
        'precipitation': 'none',
        'airport_distance': 18,
        'sensitive_areas': ['学校', '医院', '商业区'],
        'terrain_type': '平原',
        'em_interference': '弱',
        'flight_altitude': 60,
        'flight_time': 15
    },
    '杭州市': {
        'airspace_type': 'C',
        'population_density': 4800,
        'max_building_height': 380,
        'wind_speed': 3.0,
        'visibility': 9,
        'precipitation': 'none',
        'airport_distance': 22,
        'sensitive_areas': ['学校', '医院', '公园'],
        'terrain_type': '平原',
        'em_interference': '弱',
        'flight_altitude': 55,
        'flight_time': 14
    }
}
def run_rule_based_assessment(region: str) -> Dict[str, Any]:
    assessor = RuleBasedRiskAssessment()
    params = CITY_FEATURES.get(region, {})
    params['region'] = region
    return assessor.assess(params)
if __name__ == '__main__':
    for city in ['深圳市', '广州市', '上海市', '北京市', '成都市', '杭州市']:
        result = run_rule_based_assessment(city)
        print(f"\n{city}:")
        print(f"  风险评分: {result['risk_score']:.4f}")
        print(f"  风险等级: {result['risk_level']}")
        print(f"  建议:")
        for rec in result['recommendations'][:3]:
            print(f"    - {rec}")