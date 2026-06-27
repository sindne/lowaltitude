"""
增强型GIS工具 - 提供更可靠的区域边界数据获取
"""
import os
import json
import math
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from .custom_shp_reader import get_custom_shp_reader
    SHP_AVAILABLE = True
except ImportError:
    try:
        from .shp_reader import get_shp_reader
        SHP_AVAILABLE = True
    except ImportError:
        SHP_AVAILABLE = False


class EnhancedGISTool:
    """增强型GIS工具"""
    
    def __init__(self, amap_key: Optional[str] = None, postgis_db=None):
        self.amap_key = amap_key or os.environ.get('AMAP_KEY', '')
        self.cache = {}
        self.cache_lock = None
        self.shp_reader = None
        self.postgis_db = postgis_db
        
        # 优先使用定制的SHP读取器
        if SHP_AVAILABLE:
            try:
                from .custom_shp_reader import get_custom_shp_reader
                self.shp_reader = get_custom_shp_reader()
                if self.shp_reader.is_available():
                    print(f"[EnhancedGIS] 定制SHP数据已加载，共{len(self.shp_reader.data_cache)}条记录")
                else:
                    print(f"[EnhancedGIS] 定制SHP数据不可用，尝试通用读取器")
                    self.shp_reader = None
            except Exception as e:
                print(f"[EnhancedGIS] 定制SHP数据加载失败: {e}")
                self.shp_reader = None
        
        # 如果定制读取器失败，尝试通用读取器
        if self.shp_reader is None:
            try:
                from .shp_reader import get_shp_reader
                self.shp_reader = get_shp_reader()
                if self.shp_reader.is_available():
                    print(f"[EnhancedGIS] 通用SHP数据已加载，共{len(self.shp_reader.data_cache)}条记录")
                else:
                    print(f"[EnhancedGIS] SHP数据不可用")
                    self.shp_reader = None
            except Exception as e:
                print(f"[EnhancedGIS] SHP数据加载失败: {e}")
                self.shp_reader = None
    
    def get_administrative_boundary(
        self, 
        keywords: str, 
        subdistrict: int = 0,
        extensions: str = 'all',
        city_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取行政区划边界 - 增强版
        策略链: SHP → PostGIS → 多API (高德→百度→腾讯→天地图) → 简化关键词
        """
        cache_key = f"{keywords}_{subdistrict}_{extensions}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 策略0: SHP本地数据
        if self.shp_reader:
            shp_result = self.shp_reader.to_amap_format(keywords)
            if shp_result:
                self.cache[cache_key] = shp_result
                self._save_to_postgis(keywords, city_name, shp_result, 'shp')
                return shp_result
        
        # 策略0.5: PostGIS数据库缓存
        if self.postgis_db and city_name:
            pg_result = self.postgis_db.get_district_boundary(city_name, keywords)
            if pg_result and pg_result.get('polyline'):
                amap_format = {
                    'polyline': pg_result['polyline'], 'name': keywords,
                    'level': 'district',
                    'center': f"{pg_result.get('center_lng', '')},{pg_result.get('center_lat', '')}",
                    'source': 'postgis'
                }
                self.cache[cache_key] = amap_format
                return amap_format
        
        # 策略1: 多API依次尝试 (高德→百度→腾讯→天地图)
        from mcp_tools.multi_map_api import get_multi_map_api
        multi_api = get_multi_map_api(self.amap_key)
        result, source = multi_api.get_administrative_boundary(keywords, subdistrict, extensions)
        if result and self._has_valid_boundary(result):
            self.cache[cache_key] = result
            self._save_to_postgis(keywords, city_name, result, source)
            return result
        
        # 策略2: 简化关键词再试
        simplified = self._simplify_keywords(keywords)
        if simplified != keywords:
            result, source = multi_api.get_administrative_boundary(simplified, subdistrict, extensions)
            if result and self._has_valid_boundary(result):
                self.cache[cache_key] = result
                self._save_to_postgis(keywords, city_name, result, f'{source}_simplified')
                return result
        
        # 策略3: 带子区域查询
        result, source = multi_api.get_administrative_boundary(keywords, 1, extensions)
        if result and (self._has_valid_boundary(result) or result.get('districts')):
            self.cache[cache_key] = result
            return result
        
        return None
    
    def _save_to_postgis(self, district_name: str, city_name: str,
                          result: Dict[str, Any], source: str):
        """将API获取的边界数据保存到PostGIS"""
        if not self.postgis_db or not city_name:
            return
        try:
            polyline = result.get('polyline', '')
            if not polyline:
                return
            center_str = result.get('center', '')
            center_lng, center_lat = None, None
            if center_str and ',' in center_str:
                parts = center_str.split(',')
                try:
                    center_lng, center_lat = float(parts[0]), float(parts[1])
                except ValueError:
                    pass
            
            rid = self.postgis_db.add_district_boundary(
                city_name=city_name,
                district_name=district_name,
                polyline=polyline,
                center_lng=center_lng,
                center_lat=center_lat,
                adcode=result.get('adcode', ''),
                source=source
            )
            if rid:
                print(f"[EnhancedGIS] 边界已保存到PostGIS: {city_name}/{district_name} (来源:{source})")
        except Exception as e:
            print(f"[EnhancedGIS] 保存边界到PostGIS失败: {e}")
    
    def _query_amap_boundary(
        self, 
        keywords: str, 
        subdistrict: int, 
        extensions: str
    ) -> Optional[Dict[str, Any]]:
        """查询高德地图API"""
        try:
            encoded_keywords = urllib.parse.quote(keywords)
            url = f"https://restapi.amap.com/v3/config/district?key={self.amap_key}&keywords={encoded_keywords}&subdistrict={subdistrict}&extensions={extensions}"
            
            print(f"[EnhancedGIS] 查询: {keywords}")
            
            with urllib.request.urlopen(url, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('status') == '1' and data.get('districts'):
                    result = data['districts'][0]
                    print(f"[EnhancedGIS] 成功获取: {keywords}")
                    return result
        except Exception as e:
            print(f"[EnhancedGIS] 查询失败: {keywords}, 错误: {str(e)}")
        
        return None
    
    def _simplify_keywords(self, keywords: str) -> str:
        """简化关键词"""
        suffixes = ['市', '区', '县', '省', '自治区', '特别行政区']
        result = keywords
        for suffix in suffixes:
            if result.endswith(suffix):
                result = result[:-len(suffix)]
        return result
    
    def _try_parent_district(self, keywords: str, extensions: str) -> Optional[Dict[str, Any]]:
        """尝试查询上级行政区"""
        # 先查询市级
        city_result = self._query_amap_boundary(keywords, 1, extensions)
        if city_result and 'districts' in city_result and city_result['districts']:
            print(f"[EnhancedGIS] 使用市级边界: {keywords}")
            return city_result
        
        return None
    
    def _has_valid_boundary(self, district: Dict[str, Any]) -> bool:
        """检查是否有有效的边界数据"""
        if 'polyline' in district and district['polyline']:
            return True
        if 'districts' in district and district['districts']:
            for sub in district['districts']:
                if 'polyline' in sub and sub['polyline']:
                    return True
        return False
    
    def generate_fallback_boundary(
        self, 
        center_lng: float, 
        center_lat: float, 
        area_name: Optional[str] = None,
        size_factor: float = 1.0
    ) -> List[List[float]]:
        """
        生成备用边界 - 基于地理中心点的规则多边形近似
        """
        base_size = 0.08 * size_factor
        
        if area_name:
            if '区' in area_name or '县' in area_name:
                base_size = 0.05 * size_factor
            elif '市' in area_name:
                base_size = 0.15 * size_factor
            elif '省' in area_name:
                base_size = 0.5 * size_factor
        
        # 使用正八边形近似（去掉随机扰动）
        num_points = 8
        polygon = []
        
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points - math.pi / 8
            lng = center_lng + base_size * math.cos(angle)
            lat = center_lat + base_size * math.sin(angle) * 0.85
            polygon.append([lng, lat])
        
        polygon.append(polygon[0])
        return polygon
    
    def parse_polyline(self, polyline_str: str) -> List[List[List[float]]]:
        """解析高德地图polyline格式"""
        if not polyline_str:
            return []
        
        coordinates = []
        for ring in polyline_str.split('|'):
            ring_coords = []
            for point in ring.split(';'):
                if ',' in point:
                    try:
                        lng, lat = point.split(',')
                        ring_coords.append([float(lng), float(lat)])
                    except (ValueError, IndexError):
                        continue
            if ring_coords:
                coordinates.append(ring_coords)
        
        return coordinates
    
    def get_region_center(self, district: Dict[str, Any]) -> Tuple[float, float]:
        """获取区域中心点"""
        if 'center' in district and district['center']:
            try:
                lng, lat = map(float, district['center'].split(','))
                return lng, lat
            except (ValueError, IndexError):
                pass
        
        return 116.397428, 39.90923
    
    def batch_get_district_details(
        self, 
        district_names: List[str],
        max_workers: int = 8
    ) -> Dict[str, Dict[str, Any]]:
        """批量获取区县详情"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_name = {
                executor.submit(self.get_administrative_boundary, name, 0, 'all'): name
                for name in district_names
            }
            
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    result = future.result()
                    if result:
                        results[name] = result
                except Exception as e:
                    print(f"[EnhancedGIS] 批量获取失败: {name}, {str(e)}")
        
        return results


_enhanced_gis_tool: Optional[EnhancedGISTool] = None


def get_enhanced_gis_tool(amap_key: Optional[str] = None, postgis_db=None) -> EnhancedGISTool:
    """获取增强型GIS工具单例"""
    global _enhanced_gis_tool
    if _enhanced_gis_tool is None:
        _enhanced_gis_tool = EnhancedGISTool(amap_key, postgis_db)
    elif postgis_db and not _enhanced_gis_tool.postgis_db:
        _enhanced_gis_tool.postgis_db = postgis_db
    return _enhanced_gis_tool
