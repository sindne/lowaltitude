"""
数据提供者模块
用于获取城市数据、人口数据、基础设施数据等
"""
import os
import json
import math
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
import random

try:
    from .custom_shp_reader import get_custom_shp_reader
    SHP_AVAILABLE = True
except ImportError:
    SHP_AVAILABLE = False


class DataProvider:
    """数据提供者"""
    
    def __init__(self, amap_key: Optional[str] = None):
        self.amap_key = amap_key or os.environ.get('AMAP_KEY', '')
        self.shp_reader = None
        self.postgis_db = None
        self.enhanced_data_fetcher = None
        
        if SHP_AVAILABLE:
            try:
                self.shp_reader = get_custom_shp_reader()
            except Exception as e:
                print(f"[DataProvider] SHP读取器初始化失败: {e}")
    
    def set_postgis_db(self, db):
        """设置PostGIS数据库连接"""
        self.postgis_db = db
    
    def set_enhanced_data_fetcher(self, fetcher):
        """设置增强版数据获取器"""
        self.enhanced_data_fetcher = fetcher
        
        self.infrastructure_db = self._load_infrastructure_db()
        
        self.sensitive_areas_db = self._load_sensitive_areas_db()
        
        self.population_density_db = self._load_population_density_db()
        
        self.gdp_db = self._load_gdp_db()
    
    def _load_infrastructure_db(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载基础设施数据库"""
        return {
            '北京': [
                {'name': '北京首都国际机场', 'type': 'airport', 'location': [116.6083, 40.0799]},
                {'name': '北京大兴国际机场', 'type': 'airport', 'location': [116.4179, 39.5091]},
                {'name': '北京站', 'type': 'train_station', 'location': [116.4278, 39.9028]},
                {'name': '北京西站', 'type': 'train_station', 'location': [116.3221, 39.8949]},
                {'name': '北京南站', 'type': 'train_station', 'location': [116.3783, 39.8653]}
            ],
            '上海': [
                {'name': '上海虹桥国际机场', 'type': 'airport', 'location': [121.3356, 31.1946]},
                {'name': '上海浦东国际机场', 'type': 'airport', 'location': [121.8044, 31.1443]},
                {'name': '上海站', 'type': 'train_station', 'location': [121.4509, 31.2497]},
                {'name': '上海虹桥站', 'type': 'train_station', 'location': [121.3183, 31.1938]},
                {'name': '上海南站', 'type': 'train_station', 'location': [121.4321, 31.1572]}
            ],
            '广州': [
                {'name': '广州白云国际机场', 'type': 'airport', 'location': [113.2987, 23.3925]},
                {'name': '广州站', 'type': 'train_station', 'location': [113.2488, 23.1475]},
                {'name': '广州南站', 'type': 'train_station', 'location': [113.2643, 23.0021]},
                {'name': '广州东站', 'type': 'train_station', 'location': [113.3301, 23.1472]}
            ],
            '深圳': [
                {'name': '深圳宝安国际机场', 'type': 'airport', 'location': [113.8114, 22.6388]},
                {'name': '深圳站', 'type': 'train_station', 'location': [114.1112, 22.5378]},
                {'name': '深圳北站', 'type': 'train_station', 'location': [114.0282, 22.6087]},
                {'name': '福田站', 'type': 'train_station', 'location': [114.0567, 22.5403]}
            ],
            '武汉': [
                {'name': '武汉天河国际机场', 'type': 'airport', 'location': [114.2068, 30.7832]},
                {'name': '武昌火车站', 'type': 'train_station', 'location': [114.3183, 30.5307]},
                {'name': '武汉站', 'type': 'train_station', 'location': [114.4186, 30.6064]},
                {'name': '汉口火车站', 'type': 'train_station', 'location': [114.2534, 30.6208]}
            ],
            '成都': [
                {'name': '成都双流国际机场', 'type': 'airport', 'location': [103.9471, 30.5785]},
                {'name': '成都天府国际机场', 'type': 'airport', 'location': [104.4419, 30.3191]},
                {'name': '成都站', 'type': 'train_station', 'location': [104.0731, 30.6895]},
                {'name': '成都东站', 'type': 'train_station', 'location': [104.1013, 30.6215]}
            ],
            '杭州': [
                {'name': '杭州萧山国际机场', 'type': 'airport', 'location': [120.4342, 30.2282]},
                {'name': '杭州站', 'type': 'train_station', 'location': [120.1854, 30.2496]},
                {'name': '杭州东站', 'type': 'train_station', 'location': [120.2192, 30.2859]}
            ],
            '南京': [
                {'name': '南京禄口国际机场', 'type': 'airport', 'location': [118.8639, 31.7420]},
                {'name': '南京站', 'type': 'train_station', 'location': [118.7993, 32.0665]},
                {'name': '南京南站', 'type': 'train_station', 'location': [118.8023, 31.9678]}
            ],
            '长沙': [
                {'name': '长沙黄花国际机场', 'type': 'airport', 'location': [113.2278, 28.1917]},
                {'name': '长沙站', 'type': 'train_station', 'location': [112.9976, 28.1934]},
                {'name': '长沙南站', 'type': 'train_station', 'location': [113.0638, 28.1526]}
            ],
            '重庆': [
                {'name': '重庆江北国际机场', 'type': 'airport', 'location': [106.6432, 29.7192]},
                {'name': '重庆站', 'type': 'train_station', 'location': [106.5759, 29.5452]},
                {'name': '重庆北站', 'type': 'train_station', 'location': [106.6159, 29.6220]}
            ],
            '天津': [
                {'name': '天津滨海国际机场', 'type': 'airport', 'location': [117.3503, 39.1256]},
                {'name': '天津站', 'type': 'train_station', 'location': [117.2062, 39.1369]},
                {'name': '天津西站', 'type': 'train_station', 'location': [117.1769, 39.1566]}
            ],
            '西安': [
                {'name': '西安咸阳国际机场', 'type': 'airport', 'location': [108.7528, 34.4471]},
                {'name': '西安站', 'type': 'train_station', 'location': [108.9632, 34.2707]},
                {'name': '西安北站', 'type': 'train_station', 'location': [108.9560, 34.3837]}
            ],
            '青岛': [
                {'name': '青岛胶东国际机场', 'type': 'airport', 'location': [120.1007, 36.3692]},
                {'name': '青岛站', 'type': 'train_station', 'location': [120.3124, 36.0670]},
                {'name': '青岛北站', 'type': 'train_station', 'location': [120.3812, 36.1529]}
            ],
            '大连': [
                {'name': '大连周水子国际机场', 'type': 'airport', 'location': [121.5391, 38.9661]},
                {'name': '大连站', 'type': 'train_station', 'location': [121.6210, 38.9229]},
                {'name': '大连北站', 'type': 'train_station', 'location': [121.6232, 39.0074]}
            ],
            '厦门': [
                {'name': '厦门高崎国际机场', 'type': 'airport', 'location': [118.1266, 24.5401]},
                {'name': '厦门站', 'type': 'train_station', 'location': [118.1044, 24.4663]},
                {'name': '厦门北站', 'type': 'train_station', 'location': [118.0903, 24.6334]}
            ]
        }
    
    def _load_sensitive_areas_db(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载敏感区域数据库"""
        return {
            '北京': [
                {'name': '北京市政府', 'type': 'government', 'priority': 1},
                {'name': '清华大学', 'type': 'university', 'priority': 2},
                {'name': '北京大学', 'type': 'university', 'priority': 2},
                {'name': '故宫博物院', 'type': 'tourist', 'priority': 2},
                {'name': '天安门广场', 'type': 'tourist', 'priority': 1}
            ],
            '上海': [
                {'name': '上海市政府', 'type': 'government', 'priority': 1},
                {'name': '复旦大学', 'type': 'university', 'priority': 2},
                {'name': '上海交通大学', 'type': 'university', 'priority': 2},
                {'name': '外滩', 'type': 'tourist', 'priority': 2},
                {'name': '东方明珠', 'type': 'tourist', 'priority': 2}
            ],
            '广州': [
                {'name': '广州市政府', 'type': 'government', 'priority': 1},
                {'name': '中山大学', 'type': 'university', 'priority': 2},
                {'name': '华南理工大学', 'type': 'university', 'priority': 2},
                {'name': '广州塔', 'type': 'tourist', 'priority': 2},
                {'name': '白云山', 'type': 'nature_reserve', 'priority': 1}
            ],
            '深圳': [
                {'name': '深圳市政府', 'type': 'government', 'priority': 1},
                {'name': '深圳大学', 'type': 'university', 'priority': 2},
                {'name': '南方科技大学', 'type': 'university', 'priority': 2},
                {'name': '世界之窗', 'type': 'tourist', 'priority': 2}
            ],
            '武汉': [
                {'name': '湖北省政府', 'type': 'government', 'priority': 1},
                {'name': '武汉大学', 'type': 'university', 'priority': 2},
                {'name': '黄鹤楼', 'type': 'tourist', 'priority': 2},
                {'name': '东湖风景区', 'type': 'nature_reserve', 'priority': 1}
            ],
            '成都': [
                {'name': '四川省政府', 'type': 'government', 'priority': 1},
                {'name': '四川大学', 'type': 'university', 'priority': 2},
                {'name': '成都大熊猫繁育研究基地', 'type': 'nature_reserve', 'priority': 1}
            ],
            '杭州': [
                {'name': '浙江省政府', 'type': 'government', 'priority': 1},
                {'name': '浙江大学', 'type': 'university', 'priority': 2},
                {'name': '西湖风景区', 'type': 'nature_reserve', 'priority': 1}
            ],
            '南京': [
                {'name': '江苏省政府', 'type': 'government', 'priority': 1},
                {'name': '南京大学', 'type': 'university', 'priority': 2},
                {'name': '南京博物院', 'type': 'tourist', 'priority': 2}
            ],
            '长沙': [
                {'name': '湖南省政府', 'type': 'government', 'priority': 1},
                {'name': '湖南大学', 'type': 'university', 'priority': 2},
                {'name': '岳麓山', 'type': 'nature_reserve', 'priority': 1}
            ]
        }
    
    def _load_population_density_db(self) -> Dict[str, float]:
        """加载人口密度数据库（人/平方公里）"""
        return {
            '北京': 1312, '上海': 3826, '广州': 2059, '深圳': 8791,
            '武汉': 1281, '成都': 1167, '杭州': 587, '南京': 1414,
            '长沙': 1407, '重庆': 382, '天津': 1300, '西安': 1004,
            '青岛': 655, '大连': 785, '厦门': 2081
        }
    
    def _load_gdp_db(self) -> Dict[str, float]:
        """加载GDP数据库（亿元）"""
        return {
            '北京': 41610, '上海': 47211, '广州': 28839, '深圳': 32387,
            '武汉': 18866, '成都': 20818, '杭州': 18753, '南京': 16908,
            '长沙': 13966, '重庆': 29129, '天津': 15919, '西安': 11486,
            '青岛': 14921, '大连': 8431, '厦门': 7803
        }
    
    def get_city_boundary(self, city_name: str) -> Optional[Dict[str, Any]]:
        """获取城市边界数据（优先使用SHP）"""
        if self.shp_reader:
            boundary = self.shp_reader.get_boundary(city_name)
            if boundary:
                print(f"[DataProvider] 从SHP获取边界: {city_name}")
                return boundary
        
        print(f"[DataProvider] SHP中未找到边界: {city_name}")
        return None
    
    def get_infrastructure(self, city_name: str) -> List[Dict[str, Any]]:
        """获取城市基础设施数据"""
        if city_name in self.infrastructure_db:
            print(f"[DataProvider] 从本地数据库获取基础设施: {city_name}")
            return self.infrastructure_db[city_name]
        
        if self.postgis_db:
            try:
                print(f"[DataProvider] 从PostGIS查询基础设施: {city_name}")
                pg_infra = self.postgis_db.get_infrastructure(city_name)
                if pg_infra and len(pg_infra) > 0:
                    result = []
                    for infra in pg_infra:
                        result.append({
                            'name': infra.get('name'),
                            'type': infra.get('type'),
                            'location': [infra.get('lng'), infra.get('lat')] if infra.get('lng') and infra.get('lat') else None
                        })
                    print(f"[DataProvider] 从PostGIS获取到 {len(result)} 个基础设施")
                    return result
            except Exception as e:
                print(f"[DataProvider] 从PostGIS获取基础设施失败: {e}")
        
        if self.enhanced_data_fetcher:
            try:
                print(f"[DataProvider] 从API获取基础设施: {city_name}")
                api_infra = self.enhanced_data_fetcher.fetch_infrastructure_from_amap(city_name)
                if api_infra and len(api_infra) > 0:
                    for infra in api_infra:
                        if self.postgis_db:
                            try:
                                self.postgis_db.add_infrastructure(
                                    city_name,
                                    infra['name'],
                                    infra['type'],
                                    infra['location'][0] if infra['location'] else None,
                                    infra['location'][1] if infra['location'] else None,
                                    source=infra.get('source', 'amap_api')
                                )
                            except Exception as e:
                                print(f"[DataProvider] 保存基础设施到PostGIS失败: {e}")
                    
                    result = []
                    for infra in api_infra:
                        result.append({
                            'name': infra['name'],
                            'type': infra['type'],
                            'location': infra['location']
                        })
                    print(f"[DataProvider] 从API获取到 {len(result)} 个基础设施并保存")
                    return result
            except Exception as e:
                print(f"[DataProvider] 从API获取基础设施失败: {e}")
        
        print(f"[DataProvider] 基础设施数据未找到: {city_name}，使用默认数据")
        return self._generate_default_infrastructure(city_name)
    
    def _generate_default_infrastructure(self, city_name: str) -> List[Dict[str, Any]]:
        """为没有数据的城市生成默认基础设施"""
        return [
            {'name': f'{city_name}站', 'type': 'train_station', 'location': None}
        ]
    
    def get_sensitive_areas(self, city_name: str) -> List[Dict[str, Any]]:
        """获取城市敏感区域数据"""
        if city_name in self.sensitive_areas_db:
            print(f"[DataProvider] 从本地数据库获取敏感区域: {city_name}")
            return self.sensitive_areas_db[city_name]
        
        if self.postgis_db:
            try:
                print(f"[DataProvider] 从PostGIS查询敏感区域: {city_name}")
                pg_areas = self.postgis_db.get_sensitive_areas(city_name)
                if pg_areas and len(pg_areas) > 0:
                    result = []
                    for area in pg_areas:
                        result.append({
                            'name': area.get('name'),
                            'type': area.get('type'),
                            'priority': area.get('priority', 1)
                        })
                    print(f"[DataProvider] 从PostGIS获取到 {len(result)} 个敏感区域")
                    return result
            except Exception as e:
                print(f"[DataProvider] 从PostGIS获取敏感区域失败: {e}")
        
        if self.enhanced_data_fetcher:
            try:
                print(f"[DataProvider] 从API获取敏感区域: {city_name}")
                api_areas = self.enhanced_data_fetcher.fetch_sensitive_areas_from_amap(city_name)
                if api_areas and len(api_areas) > 0:
                    for area in api_areas:
                        if self.postgis_db:
                            try:
                                self.postgis_db.add_sensitive_area(
                                    city_name,
                                    area['name'],
                                    area['type'],
                                    area['location'][0] if area['location'] else None,
                                    area['location'][1] if area['location'] else None,
                                    priority=area.get('priority', 1),
                                    source=area.get('source', 'amap_api')
                                )
                            except Exception as e:
                                print(f"[DataProvider] 保存敏感区域到PostGIS失败: {e}")
                    
                    result = []
                    for area in api_areas:
                        result.append({
                            'name': area['name'],
                            'type': area['type'],
                            'priority': area.get('priority', 1)
                        })
                    print(f"[DataProvider] 从API获取到 {len(result)} 个敏感区域并保存")
                    return result
            except Exception as e:
                print(f"[DataProvider] 从API获取敏感区域失败: {e}")
        
        print(f"[DataProvider] 敏感区域数据未找到: {city_name}，使用默认数据")
        return self._generate_default_sensitive_areas(city_name)
    
    def _generate_default_sensitive_areas(self, city_name: str) -> List[Dict[str, Any]]:
        """为没有数据的城市生成默认敏感区域"""
        return [
            {'name': f'{city_name}市政府', 'type': 'government', 'priority': 1}
        ]
    
    def get_population_density(self, city_name: str) -> float:
        """获取城市人口密度（人/平方公里）"""
        if city_name in self.population_density_db:
            density = self.population_density_db[city_name]
            print(f"[DataProvider] 获取人口密度: {city_name} = {density}人/平方公里")
            return density
        
        print(f"[DataProvider] 估算人口密度: {city_name}")
        return self._estimate_population_density(city_name)
    
    def _estimate_population_density(self, city_name: str) -> float:
        """估算城市人口密度"""
        major_cities = ['北京', '上海', '广州', '深圳', '武汉', '成都', '杭州', '南京']
        if city_name in major_cities:
            return 1500.0
        return 800.0
    
    def get_gdp(self, city_name: str) -> float:
        """获取城市GDP（亿元）"""
        if city_name in self.gdp_db:
            gdp = self.gdp_db[city_name]
            print(f"[DataProvider] 获取GDP: {city_name} = {gdp}亿元")
            return gdp
        
        print(f"[DataProvider] 估算GDP: {city_name}")
        return self._estimate_gdp(city_name)
    
    def _estimate_gdp(self, city_name: str) -> float:
        """估算城市GDP"""
        major_cities = ['北京', '上海', '广州', '深圳', '武汉', '成都', '杭州', '南京']
        if city_name in major_cities:
            return 20000.0
        return 5000.0
    
    def get_city_info(self, city_name: str) -> Dict[str, Any]:
        """
        获取城市综合信息（用于AHP+LLM权重调整）
        
        Args:
            city_name: 城市名称
            
        Returns:
            城市特征数据字典，包含：
            - population_density: 人口密度（人/平方公里）
            - building_density: 建筑密度（0-1）
            - num_airports: 机场数量
            - avg_wind_speed: 平均风速（m/s）
            - terrain_complexity: 地形复杂度（0-1）
            - has_typhoon: 是否有台风
            - has_mountains: 是否有山地
        """
        population_density = self.get_population_density(city_name)
        infrastructure = self.get_infrastructure(city_name)
        
        num_airports = sum(1 for infra in infrastructure if infra.get('type') == 'airport')
        
        gdp = self.get_gdp(city_name)
        
        building_density = min(1.0, gdp / 50000.0 * 0.8 + population_density / 10000.0 * 0.2)
        
        coastal_cities = ['上海', '广州', '深圳', '青岛', '大连', '厦门', '天津', '福州', '海口', '三亚', '温州', '宁波', '汕头', '湛江']
        has_typhoon = city_name in coastal_cities
        
        mountain_cities = ['重庆', '成都', '西安', '昆明', '贵阳', '兰州', '西宁', '拉萨']
        has_mountains = city_name in mountain_cities
        
        avg_wind_speed = 5.0
        if has_typhoon:
            avg_wind_speed = 7.0
        elif city_name in ['北京', '天津', '石家庄']:
            avg_wind_speed = 6.0
        elif city_name in mountain_cities:
            avg_wind_speed = 4.5
        else:
            avg_wind_speed = 5.0
        
        geo_topology_score = self._calculate_geo_topology(city_name, infrastructure)
        
        return {
            'population_density': population_density,
            'building_density': round(building_density, 2),
            'num_airports': num_airports,
            'avg_wind_speed': avg_wind_speed,
            'geo_topology_score': geo_topology_score,
            'has_typhoon': has_typhoon,
            'has_sensitive_facilities': len(infrastructure) > 5,
            'gdp': gdp
        }
    
    def _calculate_geo_topology(self, city_name: str, infrastructure: List[Dict]) -> float:
        """
        计算地理拓扑评分
        
        地理拓扑因素主要是指目标区域与其他各种重要的设施之间的空间邻近程度：
        1. 建立基于市中心出发的距离测算模型
        2. 使用敏感设施位置数据库计算飞行航线到各个敏感设施的最近距离
        3. 如果飞行航路经过敏感设施附近一定范围或进入预设距离以内，
           则根据不同类型的敏感设施及其具体距离对风险评分进行加权
        
        Args:
            city_name: 城市名称
            infrastructure: 基础设施列表
            
        Returns:
            地理拓扑评分 (0-1)
        """
        if not infrastructure:
            return 0.3
        
        center_point = None
        for infra in infrastructure:
            if infra.get('type') in ['airport', 'train_station']:
                center_point = (infra.get('lng', 0), infra.get('lat', 0))
                break
        
        if not center_point:
            return 0.3
        
        sensitive_types = {
            'airport': 1.0,
            'government': 0.9,
            'military': 1.0,
            'hospital': 0.7,
            'school': 0.7,
            'power_plant': 0.8,
            'train_station': 0.6,
            'university': 0.5,
            'nature_reserve': 0.6
        }
        
        total_risk = 0.0
        count = 0
        
        for infra in infrastructure:
            infra_type = infra.get('type', '')
            if infra_type not in sensitive_types:
                continue
            
            infra_point = (infra.get('lng', 0), infra.get('lat', 0))
            distance = self._haversine_distance(center_point, infra_point)
            
            safety_threshold = {
                'airport': 15.0,
                'government': 5.0,
                'military': 10.0,
                'hospital': 3.0,
                'school': 2.0,
                'power_plant': 8.0,
                'train_station': 5.0,
                'university': 2.0,
                'nature_reserve': 10.0
            }.get(infra_type, 5.0)
            
            if distance < safety_threshold:
                risk_factor = sensitive_types[infra_type] * (1 - distance / safety_threshold)
                total_risk += risk_factor
                count += 1
        
        if count > 0:
            avg_risk = total_risk / count
            return min(1.0, max(0.0, avg_risk))
        else:
            return 0.3
    
    def _haversine_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """
        计算两点间的Haversine距离（公里）
        
        Args:
            point1: (经度, 纬度)
            point2: (经度, 纬度)
            
        Returns:
            距离（公里）
        """
        import math
        
        lon1, lat1 = point1
        lon2, lat2 = point2
        
        R = 6371
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat/2) * math.sin(dlat/2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dlon/2) * math.sin(dlon/2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def calculate_risk_level(self, city_name: str, sub_region_name: Optional[str] = None) -> Tuple[str, float]:
        population_density = self.get_population_density(city_name)
        gdp = self.get_gdp(city_name)
        
        pop_risk = min(1.0, population_density / 5000.0)
        
        gdp_risk = min(1.0, gdp / 50000.0)
        
        infra_count = len(self.get_infrastructure(city_name))
        infra_risk = min(1.0, infra_count / 10.0)
        
        base_risk_score = (
            pop_risk * 0.4 +
            gdp_risk * 0.3 +
            infra_risk * 0.3
        )
        
        risk_score = base_risk_score
        
        if sub_region_name:
            sub_name_lower = sub_region_name.lower()
            
            high_risk_keywords = ['中心', '市中', '商业', '金融', 'CBD', '核心', '繁华', '闹市区', '江汉', '江岸', '武昌', '硚口', '汉阳']
            medium_risk_keywords = ['开发', '工业', '园区', '科技', '新区', '经济', '洪山', '青山', '东西湖']
            low_risk_keywords = ['郊区', '远郊', '农村', '乡村', '生态', '旅游', '风景', '度假区', '蔡甸', '江夏', '黄陂', '新洲', '汉南']
            
            adjustment_factor = 0.0
            
            high_adjustment = 0.0
            for keyword in high_risk_keywords:
                if keyword in sub_region_name:
                    high_adjustment = 0.35
                    break
            
            medium_adjustment = 0.0
            for keyword in medium_risk_keywords:
                if keyword in sub_region_name:
                    medium_adjustment = 0.15
                    break
            
            low_adjustment = 0.0
            for keyword in low_risk_keywords:
                if keyword in sub_region_name:
                    low_adjustment = -0.35
                    break
            
            if high_adjustment != 0:
                adjustment_factor = high_adjustment
            elif low_adjustment != 0:
                adjustment_factor = low_adjustment
            else:
                adjustment_factor = medium_adjustment
            
            import hashlib
            name_hash = int(hashlib.md5(sub_region_name.encode('utf-8')).hexdigest()[:4], 16)
            random_factor = ((name_hash % 100) - 50) / 250.0
            adjustment_factor += random_factor
            
            risk_score = base_risk_score + adjustment_factor
            
            risk_score = max(0.05, min(0.95, risk_score))
            
            print(f"[DataProvider] 子区域风险调整: {sub_region_name}, 基础分: {base_risk_score:.3f}, 调整后: {risk_score:.3f} (调整因子: {adjustment_factor:.3f})")
        
        if risk_score < 0.25:
            risk_level = '低风险'
        elif risk_score < 0.4:
            risk_level = '较低风险'
        elif risk_score < 0.55:
            risk_level = '中等风险'
        elif risk_score < 0.75:
            risk_level = '较高风险'
        else:
            risk_level = '高风险'
        
        region_display = f"{city_name}/{sub_region_name}" if sub_region_name else city_name
        print(f"[DataProvider] 风险评估: {region_display} = {risk_level} (分数: {risk_score:.3f})")
        return risk_level, risk_score


_data_provider: Optional[DataProvider] = None


def get_data_provider(amap_key: Optional[str] = None) -> DataProvider:
    """获取数据提供者单例"""
    global _data_provider
    if _data_provider is None:
        _data_provider = DataProvider(amap_key)
    return _data_provider