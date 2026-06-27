"""
增强型空间数据获取模块
包含：地形数据、风场数据、建筑物高度数据的API获取
"""

import requests
import math
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import urllib.parse


class TerrainDataProvider:
    """
    地形数据提供者
    使用API获取DEM高程数据
    """
    
    def __init__(self, amap_key: str):
        self.amap_key = amap_key
        self.cache = {}
        self.use_fallback = False
    
    def get_elevation(self, lng: float, lat: float) -> Optional[Dict[str, Any]]:
        """
        获取指定坐标的高程数据
        
        Args:
            lng: 经度
            lat: 纬度
            
        Returns:
            高程数据字典，包含elevation(米), accuracy(精度)
        """
        cache_key = f"{lng:.4f}_{lat:.4f}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            elevation = self._get_from_amap_weather(lng, lat)
            if elevation is None:
                elevation = self._get_from_usgs(lng, lat)
            
            if elevation is not None:
                self.cache[cache_key] = elevation
                return elevation
            
            return self._get_fallback_elevation(lng, lat)
            
        except Exception as e:
            print(f"[地形数据] 获取高程失败: {e}")
            return self._get_fallback_elevation(lng, lat)
    
    def _get_from_amap_weather(self, lng: float, lat: float) -> Optional[Dict[str, Any]]:
        """
        从高德天气API获取相关地形信息
        虽然不直接提供高程，但可获取天气/风力信息辅助评估
        """
        try:
            url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={self.amap_key}&location={lng},{lat}&extensions=all"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1':
                    return {
                        'elevation': self._estimate_elevation_from_region(lng, lat),
                        'accuracy': 'estimated',
                        'source': 'amap_estimated'
                    }
            return None
        except Exception as e:
            print(f"[地形数据] 高德天气API失败: {e}")
            return None
    
    def _get_from_usgs(self, lng: float, lat: float) -> Optional[Dict[str, Any]]:
        """
        从USGS (美国地质调查局) 获取高程数据
        使用OpenTopoData API
        """
        try:
            url = f"https://api.opentopodata.org/v1/srtm90m?locations={lat},{lng}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    elevation = data['results'][0].get('elevation')
                    if elevation is not None:
                        return {
                            'elevation': round(elevation, 1),
                            'accuracy': 'high',
                            'source': 'usgs_srtm'
                        }
            return None
        except Exception as e:
            print(f"[地形数据] USGS API失败: {e}")
            return None
    
    def _estimate_elevation_from_region(self, lng: float, lat: float) -> float:
        """
        根据区域位置估算高程
        基于中国地形分区数据，支持全国主要城市
        """
        # 中国主要城市平均海拔（米）
        city_avg_elevations = {
            '北京': 43.5, '天津': 3.3, '上海': 4.5, '重庆': 259.1,
            '石家庄': 80.5, '太原': 780.0, '呼和浩特': 1050.0,
            '沈阳': 44.0, '长春': 236.8, '哈尔滨': 142.0,
            '南京': 8.9, '杭州': 41.7, '合肥': 29.8, '福州': 84.0,
            '南昌': 46.7, '济南': 57.8, '郑州': 110.4, '武汉': 23.3,
            '长沙': 44.9, '广州': 12.1, '深圳': 70.0, '南宁': 72.2,
            '海口': 14.1, '成都': 505.9, '贵阳': 1071.2, '昆明': 1891.4,
            '拉萨': 3658.0, '西安': 396.9, '兰州': 1517.2,
            '西宁': 2261.2, '银川': 1111.5, '乌鲁木齐': 800.0,
            '大连': 29.0, '青岛': 77.2, '宁波': 4.2, '厦门': 63.2,
            '苏州': 4.0, '无锡': 8.0, '常州': 5.0, '温州': 10.0,
            '绍兴': 10.0, '嘉兴': 4.0, '金华': 40.0, '台州': 5.0,
            '泉州': 8.0, '东莞': 10.0, '佛山': 5.0, '惠州': 10.0,
            '中山': 5.0, '珠海': 4.0, '江门': 20.0, '肇庆': 50.0,
            '清远': 50.0, '揭阳': 5.0, '汕头': 5.0, '湛江': 20.0,
            '茂名': 30.0, '柳州': 90.0, '桂林': 150.0, '玉林': 80.0,
            '北海': 15.0, '三亚': 7.0, '绵阳': 450.0, '德阳': 450.0,
            '宜宾': 300.0, '泸州': 250.0, '南充': 300.0, '达州': 500.0,
            '玉溪': 1600.0, '曲靖': 1880.0, '保山': 1650.0,
            '昭通': 1900.0, '丽江': 2400.0, '宝鸡': 600.0,
            '咸阳': 400.0, '渭南': 350.0, '延安': 1100.0,
            '榆林': 1100.0, '天水': 1100.0, '武威': 1500.0,
            '张掖': 1480.0, '酒泉': 1400.0, '嘉峪关': 1600.0,
            '石嘴山': 1090.0, '吴忠': 1120.0, '中卫': 1200.0,
            '克拉玛依': 270.0, '昌吉': 570.0, '哈密': 740.0,
            '喀什': 1289.0, '伊宁': 620.0
        }
        
        # 找到最近的城市
        min_distance = float('inf')
        nearest_elev = 50.0
        
        # 使用与建筑数据相同的城市中心坐标数据库
        # 先检查是否在BuildingHeightProvider中有城市中心数据库
        # 如果没有，使用默认值
        default_city_centers = {
            '北京': (116.3975, 39.9087),
            '上海': (121.4737, 31.2304),
            '广州': (113.2644, 23.1291),
            '深圳': (114.0579, 22.5431),
            '成都': (104.0668, 30.5728),
            '重庆': (106.5049, 29.5332),
            '武汉': (114.3055, 30.5931),
            '西安': (108.9398, 34.3416),
            '杭州': (120.1536, 30.2875),
            '南京': (118.7969, 32.0603)
        }
        
        # 尝试使用BuildingHeightProvider的城市中心数据库
        # 检查是否有building_provider的引用（这里我们独立使用）
        for city_name, (city_lng, city_lat) in default_city_centers.items():
            distance = math.sqrt(
                (lng - city_lng) ** 2 + 
                (lat - city_lat) ** 2
            )
            if distance < min_distance and distance < 3.0:
                min_distance = distance
                nearest_elev = city_avg_elevations.get(city_name, 50.0)
        
        # 增加距离权重
        if min_distance < 0.5:
            elevation = nearest_elev
        elif min_distance < 1.5:
            elevation = nearest_elev + min_distance * 20
        elif min_distance < 3.0:
            elevation = nearest_elev + min_distance * 40
        else:
            # 距离过远，使用中国地形分区
            elevation = self._estimate_by_china_terrain_zones(lng, lat)
        
        return elevation
    
    def _estimate_by_china_terrain_zones(self, lng: float, lat: float) -> float:
        """根据中国地形分区估算高程"""
        # 第一阶梯：青藏高原 (高海拔)
        if lng < 105 and lat < 35 and lng > 75 and lat > 25:
            return 3500.0
        
        # 第二阶梯：内蒙古高原、黄土高原、云贵高原 (中高海拔)
        elif (lng < 110 and lng > 100 and lat > 30 and lat < 40) or \
             (lng < 110 and lng > 100 and lat > 22 and lat < 30):
            return 1500.0
        
        # 第三阶梯：东部平原丘陵 (低海拔)
        elif lng > 110 and lat > 20 and lat < 45:
            return 50.0
        
        # 东北地区
        elif lng > 115 and lat > 40:
            return 100.0
        
        # 东南沿海
        elif lng > 110 and lat < 25:
            return 30.0
        
        # 西北地区
        elif lng < 100 and lat > 35:
            return 1200.0
        
        # 西南地区
        elif lng < 105 and lat > 20 and lat < 30:
            return 800.0
        
        # 默认值
        return 200.0
    
    def _get_fallback_elevation(self, lng: float, lat: float) -> Dict[str, Any]:
        """
        备用高程数据 - 基于中国城市海拔数据库估算
        """
        return {
            'elevation': self._estimate_elevation_from_region(lng, lat),
            'accuracy': 'low',
            'source': 'estimated_from_city_database'
        }
    
    def calculate_terrain_slope(self, lng1: float, lat1: float, 
                                lng2: float, lat2: float) -> Dict[str, Any]:
        """
        计算两点之间的地形坡度
        
        Returns:
            坡度数据：slope(度), slope_percent(%), grade(等级)
        """
        elev1 = self.get_elevation(lng1, lat1)
        elev2 = self.get_elevation(lng2, lat2)
        
        if elev1 is None or elev2 is None:
            return {'slope': 0, 'slope_percent': 0, 'grade': '平坦'}
        
        h1 = elev1['elevation']
        h2 = elev2['elevation']
        
        dx = abs(lng2 - lng1) * 111320 * math.cos(math.radians((lat1 + lat2) / 2))
        dy = abs(lat2 - lat1) * 110574
        distance = math.sqrt(dx ** 2 + dy ** 2)
        
        if distance == 0:
            return {'slope': 0, 'slope_percent': 0, 'grade': '平坦'}
        
        height_diff = abs(h2 - h1)
        slope_rad = math.atan2(height_diff, distance)
        slope_deg = math.degrees(slope_rad)
        slope_percent = (height_diff / distance) * 100
        
        if slope_deg < 5:
            grade = '平坦'
        elif slope_deg < 15:
            grade = '缓坡'
        elif slope_deg < 30:
            grade = '中等坡度'
        else:
            grade = '陡坡'
        
        return {
            'slope': round(slope_deg, 1),
            'slope_percent': round(slope_percent, 1),
            'grade': grade,
            'height_diff': round(height_diff, 1),
            'distance_m': round(distance, 1)
        }
    
    def assess_terrain_risk(self, lng: float, lat: float, 
                           flight_altitude: float = 100.0) -> Dict[str, Any]:
        """
        评估地形风险
        
        Args:
            lng, lat: 位置坐标
            flight_altitude: 飞行高度（米）
            
        Returns:
            地形风险评估结果
        """
        elev_data = self.get_elevation(lng, lat)
        
        if elev_data is None:
            return {
                'risk_score': 0.0,
                'risk_level': '低',
                'terrain_elevation': 0,
                'clearance': flight_altitude
            }
        
        elevation = elev_data['elevation']
        clearance = flight_altitude - elevation
        
        risk_score = 0.0
        risk_level = '低'
        
        if clearance < 30:
            risk_score = 0.8
            risk_level = '极高'
        elif clearance < 50:
            risk_score = 0.6
            risk_level = '高'
        elif clearance < 80:
            risk_score = 0.4
            risk_level = '中等'
        elif clearance < 100:
            risk_score = 0.2
            risk_level = '低'
        
        return {
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'terrain_elevation': round(elevation, 1),
            'clearance': round(clearance, 1),
            'accuracy': elev_data['accuracy'],
            'source': elev_data['source']
        }


class WindDataProvider:
    """
    风场数据提供者
    使用天气API获取风场数据
    """
    
    def __init__(self, amap_key: str):
        self.amap_key = amap_key
        self.cache = {}
        self.cache_time = {}
    
    def get_wind_data(self, lng: float, lat: float, 
                     city_name: str = None) -> Optional[Dict[str, Any]]:
        """
        获取风场数据
        
        Args:
            lng, lat: 坐标
            city_name: 城市名称（可选，优先使用）
            
        Returns:
            风场数据：wind_speed(米/秒), wind_direction(度), 
                    wind_level(风级), risk_score(风险分数)
        """
        cache_key = city_name if city_name else f"{lng:.2f}_{lat:.2f}"
        current_time = time.time()
        
        if cache_key in self.cache and cache_key in self.cache_time:
            if current_time - self.cache_time[cache_key] < 1800:
                return self.cache[cache_key]
        
        try:
            if city_name:
                wind_data = self._get_from_amap_by_city(city_name)
            else:
                wind_data = self._get_from_amap_by_location(lng, lat)
            
            if wind_data is None:
                wind_data = self._get_fallback_wind(lng, lat)
            
            if wind_data is not None:
                self.cache[cache_key] = wind_data
                self.cache_time[cache_key] = current_time
                return wind_data
            
            return self._get_fallback_wind(lng, lat)
            
        except Exception as e:
            print(f"[风场数据] 获取失败: {e}")
            return self._get_fallback_wind(lng, lat)
    
    def _get_from_amap_by_city(self, city_name: str) -> Optional[Dict[str, Any]]:
        """从高德地图天气API获取城市风场数据"""
        try:
            url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={self.amap_key}&city={urllib.parse.quote(city_name)}&extensions=base"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1' and 'lives' in data:
                    live = data['lives'][0]
                    wind_speed = self._parse_wind_speed(live.get('windpower', '0'))
                    wind_direction = self._parse_wind_direction(live.get('winddirection', 'N'))
                    
                    return self._build_wind_result(
                        wind_speed, wind_direction, 
                        live.get('weather', ''),
                        'amap_weather'
                    )
            return None
        except Exception as e:
            print(f"[风场数据] 高德天气API失败: {e}")
            return None
    
    def _get_from_amap_by_location(self, lng: float, lat: float) -> Optional[Dict[str, Any]]:
        """从高德地图天气API通过坐标获取"""
        try:
            url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={self.amap_key}&location={lng},{lat}&extensions=base"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1' and 'lives' in data:
                    live = data['lives'][0]
                    wind_speed = self._parse_wind_speed(live.get('windpower', '0'))
                    wind_direction = self._parse_wind_direction(live.get('winddirection', 'N'))
                    
                    return self._build_wind_result(
                        wind_speed, wind_direction,
                        live.get('weather', ''),
                        'amap_weather'
                    )
            return None
        except Exception as e:
            print(f"[风场数据] 高德天气API失败: {e}")
            return None
    
    def _parse_wind_speed(self, wind_power: str) -> float:
        """解析风力等级为风速（米/秒）"""
        wind_level_map = {
            '0': 0.0, '1': 1.0, '2': 2.5, '3': 4.0,
            '4': 6.5, '5': 9.0, '6': 12.0, '7': 15.5,
            '8': 19.0, '9': 23.0, '10': 27.0, '11': 31.5, '12': 36.0
        }
        
        try:
            level = str(wind_power).strip()
            return wind_level_map.get(level, 3.0)
        except:
            return 3.0
    
    def _parse_wind_direction(self, wind_dir: str) -> float:
        """解析风向为角度"""
        dir_map = {
            'N': 0, '东北': 45, '东': 90, '东南': 135,
            '南': 180, '西南': 225, '西': 270, '西北': 315
        }
        
        return dir_map.get(str(wind_dir).strip(), 0)
    
    def _build_wind_result(self, wind_speed: float, wind_direction: float,
                          weather: str, source: str) -> Dict[str, Any]:
        """构建风场结果"""
        wind_level = self._calculate_wind_level(wind_speed)
        risk_score = self._calculate_wind_risk(wind_speed, weather)
        risk_level = self._get_risk_level(risk_score)
        
        return {
            'wind_speed': round(wind_speed, 1),
            'wind_direction': round(wind_direction, 0),
            'wind_level': wind_level,
            'weather': weather,
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'source': source
        }
    
    def _calculate_wind_level(self, speed: float) -> int:
        """计算风级"""
        if speed < 0.3:
            return 0
        elif speed < 1.6:
            return 1
        elif speed < 3.4:
            return 2
        elif speed < 5.5:
            return 3
        elif speed < 8.0:
            return 4
        elif speed < 10.8:
            return 5
        elif speed < 13.9:
            return 6
        elif speed < 17.2:
            return 7
        elif speed < 20.8:
            return 8
        else:
            return 9
    
    def _calculate_wind_risk(self, wind_speed: float, weather: str) -> float:
        """计算风场风险分数"""
        risk_score = 0.0
        
        if wind_speed < 5:
            risk_score = 0.1
        elif wind_speed < 8:
            risk_score = 0.2
        elif wind_speed < 10:
            risk_score = 0.3
        elif wind_speed < 12:
            risk_score = 0.5
        elif wind_speed < 15:
            risk_score = 0.7
        else:
            risk_score = 0.9
        
        if '雷' in weather or '雨' in weather or '雪' in weather:
            risk_score = min(1.0, risk_score + 0.2)
        
        return risk_score
    
    def _get_risk_level(self, risk_score: float) -> str:
        """获取风险等级"""
        if risk_score < 0.2:
            return '低'
        elif risk_score < 0.4:
            return '中等'
        elif risk_score < 0.7:
            return '高'
        else:
            return '极高'
    
    def _get_fallback_wind(self, lng: float, lat: float) -> Dict[str, Any]:
        """备用风场数据 - 当API不可用时返回空数据"""
        return {
            'wind_speed': 0.0,
            'wind_direction': 0,
            'wind_level': 0,
            'weather': 'API不可用',
            'risk_score': 0.0,
            'risk_level': '不可评估',
            'source': 'unavailable'
        }


class BuildingHeightProvider:
    """
    建筑物高度数据提供者
    使用POI和地图API获取建筑物高度数据
    """
    
    def __init__(self, amap_key: str):
        self.amap_key = amap_key
        self.cache = {}
        
        # 全国主要城市地标建筑数据库
        self.landmark_heights = {
            # 武汉地标
            '武汉绿地中心': 475,
            '武汉中心大厦': 438,
            '武汉长江传媒大厦': 331,
            '武汉民生银行大厦': 325,
            '武汉新世界国贸大厦': 283,
            '武汉国际金融中心': 249,
            '武汉佳丽广场': 251,
            '武汉世贸大厦': 248,
            '武汉光谷广场': 180,
            '武汉火车站': 120,
            # 北京地标
            '中国尊': 528,
            '中央电视台总部大楼': 234,
            '北京国贸三期': 330,
            '北京银泰中心': 249,
            '北京财富中心': 265,
            '北京望京SOHO': 200,
            # 上海地标
            '上海中心大厦': 632,
            '上海环球金融中心': 492,
            '上海金茂大厦': 420,
            '上海东方明珠': 468,
            '上海国际金融中心': 492,
            '上海静安嘉里中心': 260,
            # 广州地标
            '广州塔': 600,
            '广州周大福金融中心': 530,
            '广州国际金融中心': 438,
            '广州中信广场': 391,
            # 深圳地标
            '平安金融中心': 593,
            '京基100': 442,
            '地王大厦': 384,
            '深圳华润大厦': 393,
            # 天津地标
            '天津周大福金融中心': 530,
            '天津国际金融中心': 337,
            '天津津塔': 336,
            # 重庆地标
            '重庆环球金融中心': 339,
            '重庆来福士广场': 355,
            '重庆万豪国际金融中心': 283,
            # 成都地标
            '成都绿地中心': 468,
            '成都IFS': 248,
            '成都环球中心': 100,
            # 杭州地标
            '杭州来福士广场': 250,
            '杭州国际办公中心': 280,
            '杭州万象城': 180,
            # 南京地标
            '南京紫峰大厦': 450,
            '南京德基广场': 338,
            '南京国际金融中心': 288,
            # 西安地标
            '西安国瑞金融中心': 350,
            '西安绿地中心': 270,
            '西安迈科商业中心': 230,
            # 长沙地标
            '长沙国际金融中心': 452,
            '长沙世茂环球金融中心': 343,
            '长沙北辰三角洲': 268,
            # 沈阳地标
            '沈阳茂业中心': 311,
            '沈阳恒隆广场': 280,
            '沈阳华润大厦': 220,
            # 大连地标
            '大连期货大厦': 243,
            '大连裕景中心': 383,
            '大连国际会议中心': 50,
            # 青岛地标
            '青岛海天中心': 369,
            '青岛国际航运中心': 240,
            '青岛财富中心': 230,
            # 厦门地标
            '厦门国际中心': 340,
            '厦门世茂海峡大厦': 300,
            '厦门建设银行大厦': 176,
            # 昆明地标
            '昆明恒隆广场': 350,
            '昆明春之眼': 407,
            '昆明南亚风情第一城': 180,
            # 南昌地标
            '南昌绿地紫峰大厦': 303,
            '南昌国际金融中心': 239,
            '南昌新地中心': 240,
            # 合肥地标
            '合肥安徽之门': 301,
            '合肥华润大厦': 280,
            '合肥新地中心': 240,
            # 石家庄地标
            '石家庄开元金融中心': 246,
            '石家庄勒泰中心': 212,
            '石家庄万象城': 200,
            # 太原地标
            '太原中海国际中心': 230,
            '太原信达国际金融中心': 266,
            '太原万达广场': 180,
            # 郑州地标
            '郑州绿地中心': 280,
            '郑州千玺广场': 280,
            '郑州华润大厦': 210,
            # 济南地标
            '济南绿地中心': 303,
            '济南华润大厦': 259,
            '济南恒隆广场': 180,
            # 贵阳地标
            '贵阳国际贸易中心': 401,
            '贵阳花果园双子塔': 406,
            '贵阳亨特国际金融中心': 250,
            # 南宁地标
            '南宁华润大厦': 403,
            '南宁龙光世纪': 381,
            '南宁地王大厦': 276,
            # 兰州地标
            '兰州红楼时代广场': 313,
            '兰州国芳百货购物广场': 160,
            '兰州万达中心': 200,
            # 银川地标
            '银川亘元万豪大厦': 216,
            '银川绿地中心': 301,
            '银川建发现代城': 150,
            # 西宁地标
            '西宁国芳百货': 180,
            '西宁万达中心': 200,
            '西宁海湖新区CBD': 150,
            # 乌鲁木齐地标
            '乌鲁木齐中天广场': 229,
            '乌鲁木齐时代广场': 200,
            '乌鲁木齐会展中心': 120,
            # 拉萨地标
            '拉萨布达拉宫': 117,
            '拉萨洲际酒店': 100,
            '拉萨火车站': 60,
            # 呼和浩特地标
            '呼和浩特海亮广场': 176,
            '呼和浩特万象城': 200,
            '呼和浩特万达广场': 150,
            # 长春地标
            '长春国际金融中心': 226,
            '长春宏汇国际广场': 213,
            '长春卓展购物中心': 180,
            # 哈尔滨地标
            '哈尔滨富力江湾新城': 288,
            '哈尔滨国际会展体育中心': 120,
            '哈尔滨哈西万达广场': 180,
            # 福州地标
            '福州世茂天城': 273,
            '福州国际金融中心': 250,
            '福州三迪联邦大厦': 240,
            # 海口地标
            '海口海航国际广场': 249,
            '海口置地东方广场': 211,
            '海口国贸中心': 150
        }
        
        # 全国主要城市中心坐标数据库
        self.city_centers = {
            '北京': (116.3975, 39.9087),
            '天津': (117.2008, 39.0842),
            '上海': (121.4737, 31.2304),
            '重庆': (106.5049, 29.5332),
            '石家庄': (114.5148, 38.0423),
            '太原': (112.5489, 37.8706),
            '呼和浩特': (111.7519, 40.8414),
            '沈阳': (123.4328, 41.8045),
            '长春': (125.3245, 43.8868),
            '哈尔滨': (126.5356, 45.8038),
            '南京': (118.7969, 32.0603),
            '杭州': (120.1536, 30.2875),
            '合肥': (117.2272, 31.8206),
            '福州': (119.3062, 26.0753),
            '南昌': (115.8922, 28.6765),
            '济南': (117.0009, 36.6763),
            '郑州': (113.6254, 34.7466),
            '武汉': (114.3055, 30.5931),
            '长沙': (112.9388, 28.2282),
            '广州': (113.2644, 23.1291),
            '深圳': (114.0579, 22.5431),
            '南宁': (108.3275, 22.8154),
            '海口': (110.3492, 20.0462),
            '成都': (104.0668, 30.5728),
            '贵阳': (106.6301, 26.5705),
            '昆明': (102.7122, 25.0406),
            '拉萨': (91.1322, 29.6603),
            '西安': (108.9398, 34.3416),
            '兰州': (103.8343, 36.0611),
            '西宁': (101.7784, 36.6171),
            '银川': (106.2781, 38.4683),
            '乌鲁木齐': (87.6168, 43.8256),
            '大连': (121.6147, 38.9140),
            '青岛': (120.3826, 36.0671),
            '宁波': (121.5498, 29.8683),
            '厦门': (118.0919, 24.4797),
            '苏州': (120.6195, 31.2989),
            '无锡': (120.3119, 31.4912),
            '常州': (119.9740, 31.8107),
            '温州': (120.6721, 28.0005),
            '绍兴': (120.5806, 30.0300),
            '嘉兴': (120.7340, 30.7452),
            '金华': (119.6455, 29.0886),
            '台州': (121.4286, 28.6564),
            '泉州': (118.5853, 24.9097),
            '东莞': (113.8754, 23.0207),
            '佛山': (113.1221, 23.0219),
            '惠州': (114.4172, 23.1121),
            '中山': (113.3835, 22.5186),
            '珠海': (113.5491, 22.2249),
            '江门': (113.0930, 22.5862),
            '肇庆': (112.4712, 23.0462),
            '清远': (113.0514, 23.6818),
            '揭阳': (116.3756, 23.5514),
            '汕头': (116.7088, 23.3539),
            '湛江': (110.3593, 21.2707),
            '茂名': (110.9205, 21.6636),
            '柳州': (109.4164, 24.3139),
            '桂林': (110.2994, 25.2741),
            '玉林': (110.1541, 22.6314),
            '北海': (109.1195, 21.4740),
            '海口': (110.3492, 20.0462),
            '三亚': (109.5119, 18.2528),
            '绵阳': (104.7255, 31.4716),
            '德阳': (104.4030, 31.1272),
            '宜宾': (104.6300, 28.7635),
            '泸州': (105.4395, 28.8890),
            '南充': (106.0841, 30.8375),
            '达州': (107.4650, 31.2080),
            '玉溪': (102.5524, 24.3522),
            '曲靖': (103.7972, 25.5015),
            '保山': (99.1635, 25.1181),
            '昭通': (103.7153, 27.3375),
            '丽江': (100.2299, 26.8721),
            '宝鸡': (107.1480, 34.3670),
            '咸阳': (108.7056, 34.3290),
            '渭南': (109.5049, 34.4995),
            '延安': (109.4901, 36.5959),
            '榆林': (109.7400, 38.2900),
            '天水': (105.7246, 34.5766),
            '武威': (102.6356, 37.9291),
            '张掖': (100.4551, 38.9278),
            '酒泉': (98.5000, 39.7333),
            '嘉峪关': (98.2892, 39.7733),
            '石嘴山': (106.3889, 39.0324),
            '吴忠': (106.1842, 37.9938),
            '中卫': (105.1915, 37.5190),
            '克拉玛依': (84.8739, 45.5871),
            '昌吉': (87.2917, 44.0127),
            '哈密': (93.5167, 42.8333),
            '喀什': (75.9897, 39.4704),
            '伊宁': (81.3300, 43.9200)
        }
    
    def get_building_height(self, lng: float, lat: float, 
                          name: str = None) -> Optional[Dict[str, Any]]:
        """
        获取建筑物高度
        
        Args:
            lng, lat: 坐标
            name: 建筑物名称（可选）
            
        Returns:
            建筑物高度数据
        """
        cache_key = name if name else f"{lng:.4f}_{lat:.4f}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            if name:
                height_data = self._get_by_name(name)
            else:
                height_data = self._get_by_location(lng, lat)
            
            if height_data is None:
                height_data = self._estimate_height(lng, lat, name)
            
            if height_data is not None:
                self.cache[cache_key] = height_data
                return height_data
            
            return self._get_fallback_height()
            
        except Exception as e:
            print(f"[建筑数据] 获取高度失败: {e}")
            return self._get_fallback_height()
    
    def _get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """通过名称查找地标建筑高度"""
        for landmark, height in self.landmark_heights.items():
            if landmark in name or name in landmark:
                return {
                    'height': height,
                    'name': landmark,
                    'source': 'landmark_database',
                    'confidence': 'high'
                }
        
        return None
    
    def _get_by_location(self, lng: float, lat: float) -> Optional[Dict[str, Any]]:
        """通过坐标从高德POI查找"""
        try:
            url = f"https://restapi.amap.com/v3/place/around?key={self.amap_key}&location={lng},{lat}&radius=500&types=大厦|大楼|广场|建筑&offset=10"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1' and 'pois' in data:
                    pois = data['pois']
                    for poi in pois[:3]:
                        poi_name = poi.get('name', '')
                        height_data = self._get_by_name(poi_name)
                        if height_data:
                            return height_data
                    
                    if pois:
                        return self._estimate_from_poi_type(pois[0])
            
            return None
        except Exception as e:
            print(f"[建筑数据] 高德POI失败: {e}")
            return None
    
    def _estimate_from_poi_type(self, poi: Dict) -> Dict[str, Any]:
        """从POI类型估算高度"""
        poi_type = poi.get('type', '')
        
        if '超高层' in poi_type or '地标' in poi_type:
            height = 200
        elif '大厦' in poi.get('name', '') or '大楼' in poi.get('name', ''):
            height = 100
        elif '商业' in poi_type or '广场' in poi.get('name', ''):
            height = 80
        elif '住宅' in poi_type:
            height = 50
        else:
            height = 30
        
        return {
            'height': height,
            'name': poi.get('name', '未知建筑'),
            'source': 'poi_estimated',
            'confidence': 'medium'
        }
    
    def _estimate_height(self, lng: float, lat: float, name: str = None) -> Dict[str, Any]:
        """估算建筑物高度（支持全国城市）"""
        
        # 1. 首先确定最近的城市中心
        city_center = self._find_nearest_city_center(lng, lat)
        
        if city_center:
            city_name, (city_lng, city_lat) = city_center
            dist_from_center = math.sqrt(
                (lng - city_lng) ** 2 + 
                (lat - city_lat) ** 2
            )
            
            # 根据距离城市中心的距离估算高度
            if dist_from_center < 0.05:
                height = 180
            elif dist_from_center < 0.1:
                height = 120
            elif dist_from_center < 0.2:
                height = 80
            else:
                height = 40
        else:
            # 如果找不到城市中心，使用默认值
            height = 50
        
        # 特殊地标关键词检测
        if name:
            if '绿地' in name or '中心' in name or '塔' in name:
                height = max(height, 250)
            elif '大厦' in name or '大楼' in name:
                height = max(height, 100)
            elif '广场' in name or '商业' in name:
                height = max(height, 80)
        
        return {
            'height': height,
            'name': name if name else '区域建筑',
            'source': 'spatial_estimated',
            'confidence': 'low'
        }
    
    def _find_nearest_city_center(self, lng: float, lat: float) -> Optional[Tuple[str, Tuple[float, float]]]:
        """找到最近的城市中心坐标"""
        min_distance = float('inf')
        nearest_city = None
        
        for city_name, (city_lng, city_lat) in self.city_centers.items():
            distance = math.sqrt(
                (lng - city_lng) ** 2 + 
                (lat - city_lat) ** 2
            )
            if distance < min_distance and distance < 2.0:  # 2度范围内（约220公里）
                min_distance = distance
                nearest_city = (city_name, (city_lng, city_lat))
        
        return nearest_city
    
    def _get_fallback_height(self) -> Dict[str, Any]:
        """备用建筑高度数据 - 当API不可用时返回空数据"""
        return {
            'height': 0,
            'name': '数据不可用',
            'source': 'unavailable',
            'confidence': 'low'
        }
    
    def assess_building_risk(self, lng: float, lat: float, 
                           flight_altitude: float = 100.0,
                           name: str = None) -> Dict[str, Any]:
        """
        评估建筑物风险
        
        Args:
            lng, lat: 位置
            flight_altitude: 飞行高度
            name: 建筑名称
            
        Returns:
            建筑风险评估结果
        """
        height_data = self.get_building_height(lng, lat, name)
        
        if height_data is None:
            return {
                'risk_score': 0.0,
                'risk_level': '低',
                'building_height': 0,
                'clearance': flight_altitude
            }
        
        building_height = height_data['height']
        clearance = flight_altitude - building_height
        
        risk_score = 0.0
        risk_level = '低'
        
        if clearance < 20:
            risk_score = 0.9
            risk_level = '极高'
        elif clearance < 40:
            risk_score = 0.7
            risk_level = '高'
        elif clearance < 60:
            risk_score = 0.5
            risk_level = '中等'
        elif clearance < 80:
            risk_score = 0.3
            risk_level = '低'
        
        return {
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'building_height': building_height,
            'clearance': max(0, round(clearance, 1)),
            'building_name': height_data.get('name', ''),
            'source': height_data.get('source', ''),
            'confidence': height_data.get('confidence', '')
        }


class EnhancedSpatialData:
    """
    增强型空间数据管理器
    整合地形、风场、建筑物数据
    """
    
    def __init__(self, amap_key: str):
        self.amap_key = amap_key
        self.terrain_provider = TerrainDataProvider(amap_key)
        self.wind_provider = WindDataProvider(amap_key)
        self.building_provider = BuildingHeightProvider(amap_key)
    
    def get_combined_risk_assessment(self, lng: float, lat: float,
                                    flight_altitude: float = 100.0,
                                    city_name: str = None,
                                    building_name: str = None) -> Dict[str, Any]:
        """
        获取综合风险评估
        
        Args:
            lng, lat: 位置坐标
            flight_altitude: 飞行高度
            city_name: 城市名称
            building_name: 建筑物名称
            
        Returns:
            综合风险评估结果
        """
        terrain_risk = self.terrain_provider.assess_terrain_risk(lng, lat, flight_altitude)
        wind_data = self.wind_provider.get_wind_data(lng, lat, city_name)
        building_risk = self.building_provider.assess_building_risk(
            lng, lat, flight_altitude, building_name
        )
        
        terrain_score = terrain_risk.get('risk_score', 0.0)
        wind_score = wind_data.get('risk_score', 0.0) if wind_data else 0.0
        building_score = building_risk.get('risk_score', 0.0)
        
        weights = {
            'terrain': 0.25,
            'wind': 0.35,
            'building': 0.40
        }
        
        total_risk_score = (
            terrain_score * weights['terrain'] +
            wind_score * weights['wind'] +
            building_score * weights['building']
        )
        
        if total_risk_score < 0.2:
            overall_risk_level = '低'
        elif total_risk_score < 0.4:
            overall_risk_level = '中等'
        elif total_risk_score < 0.7:
            overall_risk_level = '高'
        else:
            overall_risk_level = '极高'
        
        dominant_factor = max(
            [('地形', terrain_score), ('风场', wind_score), ('建筑', building_score)],
            key=lambda x: x[1]
        )
        
        return {
            'overall_risk_score': round(total_risk_score, 2),
            'overall_risk_level': overall_risk_level,
            'dominant_risk_factor': dominant_factor[0],
            'terrain': terrain_risk,
            'wind': wind_data,
            'building': building_risk,
            'weights': weights
        }


_enhanced_spatial_data = None


def get_enhanced_spatial_data(amap_key: str) -> EnhancedSpatialData:
    """获取增强型空间数据管理器单例"""
    global _enhanced_spatial_data
    if _enhanced_spatial_data is None:
        _enhanced_spatial_data = EnhancedSpatialData(amap_key)
    return _enhanced_spatial_data
