"""
增强版数据获取模块
从API获取数据，存储到PostGIS数据库
"""
import sys
import os
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EnhancedDataFetcher:
    """增强版数据获取器"""
    
    def __init__(self, amap_key: Optional[str] = None):
        self.amap_key = amap_key or os.environ.get('AMAP_KEY', '0b138faf337795363b9a7e96d7c79301')
        self._postgis_db = None
    
    def set_postgis_db(self, db):
        """设置PostGIS数据库连接"""
        self._postgis_db = db
    
    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """发送HTTP请求"""
        try:
            if params:
                url += '?' + urllib.parse.urlencode(params)
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            print(f"[EnhancedDataFetcher] 请求失败: {url}, 错误: {e}")
            return None
    
    def fetch_city_info_from_amap(self, city_name: str) -> Optional[Dict]:
        """
        从高德地图API获取城市信息
        
        Args:
            city_name: 城市名称
            
        Returns:
            城市信息字典
        """
        print(f"[EnhancedDataFetcher] 从高德API获取城市信息: {city_name}")
        
        url = "https://restapi.amap.com/v3/config/district"
        params = {
            'key': self.amap_key,
            'keywords': city_name,
            'subdistrict': 1,
            'extensions': 'base'
        }
        
        data = self._make_request(url, params)
        
        if data and data.get('status') == '1' and data.get('districts'):
            district = data['districts'][0]
            result = {
                'name': district.get('name', city_name),
                'adcode': district.get('adcode', ''),
                'center': district.get('center', ''),
                'level': district.get('level', ''),
                'province': district.get('province', ''),
                'citycode': district.get('citycode', '')
            }
            
            # 解析中心坐标
            if result['center']:
                try:
                    lng, lat = map(float, result['center'].split(','))
                    result['center_lng'] = lng
                    result['center_lat'] = lat
                except:
                    pass
            
            print(f"[EnhancedDataFetcher] 成功获取城市信息: {result}")
            return result
        
        print(f"[EnhancedDataFetcher] 无法获取城市信息: {city_name}")
        return None
    
    def fetch_infrastructure_from_amap(self, city_name: str, keywords: List[str] = None) -> List[Dict]:
        """
        从高德地图API获取基础设施数据
        
        Args:
            city_name: 城市名称
            keywords: 搜索关键词列表
            
        Returns:
            基础设施列表
        """
        if keywords is None:
            keywords = ['机场', '火车站', '高铁站', '地铁站', '汽车站', '港口',
                       '高速公路入口', '桥梁', '隧道', '立交桥']
        
        print(f"[EnhancedDataFetcher] 从高德API获取基础设施: {city_name}")
        
        all_infrastructure = []
        
        for keyword in keywords:
            url = "https://restapi.amap.com/v3/place/text"
            params = {
                'key': self.amap_key,
                'keywords': f"{city_name}{keyword}",
                'city': city_name,
                'offset': 30,
                'page': 1
            }
            
            data = self._make_request(url, params)
            
            if data and data.get('status') == '1' and data.get('pois'):
                for poi in data['pois']:
                    try:
                        location = poi.get('location', '')
                        lng, lat = None, None
                        if location:
                            lng, lat = map(float, location.split(','))
                        
                        infra_type = self._classify_infrastructure_type(keyword, poi.get('type', ''))
                        
                        infrastructure = {
                            'name': poi.get('name', ''),
                            'type': infra_type,
                            'location': [lng, lat] if lng and lat else None,
                            'address': poi.get('address', ''),
                            'source': 'amap_api'
                        }
                        
                        if infrastructure['name'] and infrastructure['location']:
                            all_infrastructure.append(infrastructure)
                            print(f"[EnhancedDataFetcher] 获取到基础设施: {infrastructure['name']}")
                    
                    except Exception as e:
                        print(f"[EnhancedDataFetcher] 解析POI失败: {e}")
            
            time.sleep(0.1)  # 避免请求过快
        
        print(f"[EnhancedDataFetcher] 共获取到 {len(all_infrastructure)} 个基础设施")
        return all_infrastructure
    
    def _classify_infrastructure_type(self, keyword: str, poi_type: str) -> str:
        """分类基础设施类型"""
        type_mapping = {
            '机场': 'airport',
            '火车站': 'train_station',
            '高铁站': 'train_station',
            '地铁站': 'subway_station',
            '汽车站': 'bus_station',
            '港口': 'port',
            '高速公路': 'highway_entrance',
            '桥梁': 'bridge',
            '隧道': 'tunnel',
            '立交桥': 'overpass'
        }
        
        for kw, infra_type in type_mapping.items():
            if kw in keyword:
                return infra_type
        
        return 'other'
    
    def fetch_sensitive_areas_from_amap(self, city_name: str, keywords: List[str] = None) -> List[Dict]:
        """
        从高德地图API获取敏感区域数据
        
        Args:
            city_name: 城市名称
            keywords: 搜索关键词列表
            
        Returns:
            敏感区域列表
        """
        if keywords is None:
            keywords = ['政府', '大学', '医院', '景点', '体育馆',
                       '学校', '商场', '公园', '博物馆', '广场', '大型社区']
        
        print(f"[EnhancedDataFetcher] 从高德API获取敏感区域: {city_name}")
        
        all_sensitive_areas = []
        
        for keyword in keywords:
            url = "https://restapi.amap.com/v3/place/text"
            params = {
                'key': self.amap_key,
                'keywords': f"{city_name}{keyword}",
                'city': city_name,
                'offset': 30,
                'page': 1
            }
            
            data = self._make_request(url, params)
            
            if data and data.get('status') == '1' and data.get('pois'):
                for poi in data['pois']:
                    try:
                        location = poi.get('location', '')
                        lng, lat = None, None
                        if location:
                            lng, lat = map(float, location.split(','))
                        
                        area_type = self._classify_sensitive_area_type(keyword, poi.get('type', ''))
                        priority = self._determine_priority(area_type)
                        
                        sensitive_area = {
                            'name': poi.get('name', ''),
                            'type': area_type,
                            'location': [lng, lat] if lng and lat else None,
                            'address': poi.get('address', ''),
                            'priority': priority,
                            'source': 'amap_api'
                        }
                        
                        if sensitive_area['name'] and sensitive_area['location']:
                            all_sensitive_areas.append(sensitive_area)
                            print(f"[EnhancedDataFetcher] 获取到敏感区域: {sensitive_area['name']}")
                    
                    except Exception as e:
                        print(f"[EnhancedDataFetcher] 解析POI失败: {e}")
            
            time.sleep(0.1)  # 避免请求过快
        
        print(f"[EnhancedDataFetcher] 共获取到 {len(all_sensitive_areas)} 个敏感区域")
        return all_sensitive_areas
    
    def _classify_sensitive_area_type(self, keyword: str, poi_type: str) -> str:
        """分类敏感区域类型"""
        type_mapping = {
            '政府': 'government',
            '大学': 'university',
            '医院': 'hospital',
            '景点': 'tourist',
            '体育馆': 'stadium',
            '学校': 'school',
            '商场': 'commercial',
            '公园': 'nature_reserve',
            '博物馆': 'tourist',
            '广场': 'public_square',
            '大型社区': 'community'
        }
        
        for kw, area_type in type_mapping.items():
            if kw in keyword:
                return area_type
        
        return 'other'
    
    def _determine_priority(self, area_type: str) -> int:
        """确定敏感区域优先级"""
        priority_map = {
            'government': 1,
            'hospital': 1,
            'stadium': 2,
            'university': 2,
            'tourist': 2
        }
        return priority_map.get(area_type, 3)
    
    def fetch_and_save_city_data(self, city_name: str) -> bool:
        """
        获取并保存城市所有数据到PostGIS
        
        Args:
            city_name: 城市名称
            
        Returns:
            是否成功
        """
        print(f"[EnhancedDataFetcher] 开始获取并保存城市数据: {city_name}")
        
        if not self._postgis_db:
            print("[EnhancedDataFetcher] 错误: PostGIS数据库未设置")
            return False
        
        try:
            # 1. 获取城市基本信息
            city_info = self.fetch_city_info_from_amap(city_name)
            city_id = None
            if city_info:
                # 保存城市到PostGIS
                city_id = self._postgis_db.add_city(
                    name=city_info.get('name', city_name),
                    province=city_info.get('province', ''),
                    center_lng=city_info.get('center_lng'),
                    center_lat=city_info.get('center_lat'),
                    city_code=city_info.get('citycode', ''),
                    area=None,
                    boundary_coords=None
                )
                if city_id:
                    print(f"[EnhancedDataFetcher] 城市已保存到PostGIS: {city_name} (ID: {city_id})")
            
            # 2. 获取并保存基础设施
            infrastructure = self.fetch_infrastructure_from_amap(city_name)
            for infra in infrastructure:
                if self._postgis_db and city_id:
                    self._postgis_db.add_infrastructure(
                        city_id=city_id,
                        name=infra['name'],
                        infra_type=infra['type'],
                        lng=infra['location'][0] if infra['location'] else None,
                        lat=infra['location'][1] if infra['location'] else None,
                        description=infra.get('source', 'amap_api')
                    )
            
            # 3. 获取并保存敏感区域
            sensitive_areas = self.fetch_sensitive_areas_from_amap(city_name)
            for area in sensitive_areas:
                if self._postgis_db and city_id:
                    self._postgis_db.add_sensitive_area(
                        city_id=city_id,
                        name=area['name'],
                        area_type=area['type'],
                        lng=area['location'][0] if area['location'] else None,
                        lat=area['location'][1] if area['location'] else None,
                        priority=area['priority'],
                        description=area.get('source', 'amap_api')
                    )
            
            print(f"[EnhancedDataFetcher] 城市数据获取并保存完成: {city_name}")
            return True
            
        except Exception as e:
            print(f"[EnhancedDataFetcher] 获取并保存城市数据失败: {city_name}, 错误: {e}")
            import traceback
            traceback.print_exc()
            return False


_enhanced_data_fetcher: Optional[EnhancedDataFetcher] = None


def get_enhanced_data_fetcher(amap_key: Optional[str] = None) -> EnhancedDataFetcher:
    """获取增强版数据获取器单例"""
    global _enhanced_data_fetcher
    if _enhanced_data_fetcher is None:
        _enhanced_data_fetcher = EnhancedDataFetcher(amap_key)
    return _enhanced_data_fetcher
