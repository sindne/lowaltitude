from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
@dataclass
class WeatherData:
    condition: Optional[str] = None
    temperature: Optional[str] = None
    humidity: Optional[str] = None
    wind_speed: Optional[str] = None
    visibility: Optional[float] = None
    report_time: Optional[str] = None
@dataclass
class TerrainData:
    elevation: Optional[float] = None
    complexity: Optional[str] = None
    land_cover: Optional[str] = None
@dataclass
class PopulationData:
    density: Optional[float] = None
    urban_level: Optional[str] = None
    building_density: Optional[float] = None
class EnvironmentalFactorsProcessor:
    def __init__(self):
        self.weather_risk_weights = {'晴天': 0.0, '多云': 0.1, '阴': 0.2, '小雨': 0.3, '中雨': 0.5, '大雨': 0.7, '暴雨': 0.9, '雷阵雨': 0.8, '雾': 0.6, '霾': 0.5, '雪': 0.6, '冻雨': 0.8}
        self.terrain_risk_weights = {'平坦': 0.1, '轻微起伏': 0.2, '中等起伏': 0.4, '复杂': 0.7, '非常复杂': 0.9}
        self.population_risk_weights = {'低密度': 0.1, '中低密度': 0.3, '中等密度': 0.5, '中高密度': 0.7, '高密度': 0.9}
    def process_weather_data(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        condition = weather_data.get('condition', '未知')
        temperature = weather_data.get('temperature', 0.0)
        humidity = weather_data.get('humidity', 0.0)
        wind_speed = weather_data.get('wind_speed', 0.0)
        if isinstance(temperature, str):
            temperature = float(temperature.replace('°C', ''))
        if isinstance(humidity, str):
            humidity = float(humidity.replace('%', ''))
        if isinstance(wind_speed, str):
            wind_speed = self._parse_wind_speed(wind_speed)
        weather_risk = self._calculate_weather_risk(condition, temperature, humidity, wind_speed)
        return {'condition': condition, 'temperature_c': temperature, 'humidity_pct': humidity, 'wind_speed_ms': wind_speed, 'risk_score': round(weather_risk, 3), 'risk_level': self._score_to_level(weather_risk), 'assessment': self._generate_weather_assessment(condition, weather_risk)}
    def _parse_wind_speed(self, wind_speed_str: str) -> float:
        if '级' in wind_speed_str:
            level = float(wind_speed_str.replace('级', ''))
            if level <= 3:
                return 5.0
            elif level <= 5:
                return 8.0
            elif level <= 7:
                return 13.9
            else:
                return 20.0
        return float(wind_speed_str)
    def _calculate_weather_risk(self, condition: str, temperature: float, humidity: float, wind_speed: float) -> float:
        base_risk = self.weather_risk_weights.get(condition, 0.3)
        temp_risk = 0.0
        if temperature < 0 or temperature > 35:
            temp_risk = 0.3
        elif temperature < 5 or temperature > 30:
            temp_risk = 0.15
        humidity_risk = 0.0
        if humidity > 90:
            humidity_risk = 0.2
        elif humidity > 70:
            humidity_risk = 0.1
        wind_risk = 0.0
        if wind_speed > 15:
            wind_risk = 0.4
        elif wind_speed > 10:
            wind_risk = 0.2
        elif wind_speed > 5:
            wind_risk = 0.1
        total_risk = base_risk * 0.5 + temp_risk * 0.15 + humidity_risk * 0.15 + wind_risk * 0.2
        return min(1.0, max(0.0, total_risk))
    def process_terrain_data(self, terrain_data: Dict[str, Any]) -> Dict[str, Any]:
        elevation = terrain_data.get('elevation', 0.0)
        complexity = terrain_data.get('complexity', '平坦')
        terrain_risk = self._calculate_terrain_risk(elevation, complexity)
        return {'elevation_m': elevation, 'complexity': complexity, 'risk_score': round(terrain_risk, 3), 'risk_level': self._score_to_level(terrain_risk), 'assessment': self._generate_terrain_assessment(complexity, terrain_risk)}
    def _calculate_terrain_risk(self, elevation: float, complexity: str) -> float:
        base_risk = self.terrain_risk_weights.get(complexity, 0.3)
        elevation_risk = 0.0
        if elevation > 2000:
            elevation_risk = 0.3
        elif elevation > 1000:
            elevation_risk = 0.15
        total_risk = base_risk * 0.8 + elevation_risk * 0.2
        return min(1.0, max(0.0, total_risk))
    def process_population_data(self, population_data: Dict[str, Any]) -> Dict[str, Any]:
        density = population_data.get('density', 0.0)
        urban_level = population_data.get('urban_level', '低密度')
        population_risk = self._calculate_population_risk(density, urban_level)
        return {'density_people_km2': density, 'urban_level': urban_level, 'risk_score': round(population_risk, 3), 'risk_level': self._score_to_level(population_risk), 'assessment': self._generate_population_assessment(urban_level, population_risk)}
    def _calculate_population_risk(self, density: float, urban_level: str) -> float:
        base_risk = self.population_risk_weights.get(urban_level, 0.5)
        density_risk = 0.0
        if density > 5000:
            density_risk = 0.3
        elif density > 1000:
            density_risk = 0.15
        total_risk = base_risk * 0.8 + density_risk * 0.2
        return min(1.0, max(0.0, total_risk))
    def integrate_all_factors(self, weather_result: Dict[str, Any], terrain_result: Dict[str, Any], population_result: Dict[str, Any], weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        if weights is None:
            weights = {'weather': 0.35, 'terrain': 0.25, 'population': 0.4}
        weather_score = weather_result.get('risk_score', 0.5)
        terrain_score = terrain_result.get('risk_score', 0.5)
        population_score = population_result.get('risk_score', 0.5)
        total_score = weather_score * weights['weather'] + terrain_score * weights['terrain'] + population_score * weights['population']
        risk_level = self._score_to_level(total_score)
        return {'weather': weather_result, 'terrain': terrain_result, 'population': population_result, 'weights': weights, 'total_risk_score': round(total_score, 3), 'overall_risk_level': risk_level, 'integrated_assessment': self._generate_integrated_assessment(total_score, risk_level), 'analysis_timestamp': datetime.now().isoformat()}
    def _score_to_level(self, score: float) -> str:
        if score < 0.2:
            return '低风险'
        elif score < 0.4:
            return '较低风险'
        elif score < 0.6:
            return '中等风险'
        elif score < 0.8:
            return '较高风险'
        else:
            return '高风险'
    def _generate_weather_assessment(self, condition: str, risk: float) -> str:
        if risk < 0.2:
            return f'天气条件良好({condition})，适合飞行'
        elif risk < 0.5:
            return f'天气条件一般({condition})，需谨慎飞行'
        else:
            return f'天气条件较差({condition})，不建议飞行'
    def _generate_terrain_assessment(self, complexity: str, risk: float) -> str:
        if risk < 0.2:
            return f'地形条件良好({complexity})，适合飞行'
        elif risk < 0.5:
            return f'地形条件一般({complexity})，需注意地形变化'
        else:
            return f'地形条件复杂({complexity})，存在较大风险'
    def _generate_population_assessment(self, urban_level: str, risk: float) -> str:
        if risk < 0.2:
            return f'人口密度较低({urban_level})，风险较小'
        elif risk < 0.5:
            return f'人口密度中等({urban_level})，需保持安全高度'
        else:
            return f'人口密度较高({urban_level})，存在较大安全隐患'
    def _generate_integrated_assessment(self, total_score: float, risk_level: str) -> str:
        if total_score < 0.2:
            return f'综合风险评估为{risk_level}，各环境因素均在安全范围内，适合执行飞行任务'
        elif total_score < 0.5:
            return f'综合风险评估为{risk_level}，部分环境因素存在一定风险，建议采取相应防范措施后执行任务'
        else:
            return f'综合风险评估为{risk_level}，多项环境因素存在较高风险，建议暂缓飞行任务或制定详细应急预案'
_env_factors_instance = None
def get_environmental_factors_processor() -> EnvironmentalFactorsProcessor:
    global _env_factors_instance
    if _env_factors_instance is None:
        _env_factors_instance = EnvironmentalFactorsProcessor()
    return _env_factors_instance
