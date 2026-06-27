"""
多地图API支持 - 统一管理多个国内地图API
支持高德地图、百度地图、腾讯地图、天地图
"""
import os
import json
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
import math
import random


class MultiMapAPI:
    """多地图API管理器 — 依次尝试高德、百度、腾讯、天地图"""
    
    def __init__(self, amap_key=None, baidu_key=None, tencent_key=None, tianditu_key=None):
        self.amap_key = amap_key or os.environ.get('AMAP_KEY', '')
        self.baidu_key = baidu_key or os.environ.get('BAIDU_MAP_KEY', '')
        self.tencent_key = tencent_key or os.environ.get('TENCENT_MAP_KEY', '')
        self.tianditu_key = tianditu_key or os.environ.get('TIANDITU_KEY', '')
        self.cache = {}
        self.api_order = ['amap', 'baidu', 'tencent', 'tianditu']
    
    def get_administrative_boundary(
        self, 
        keywords: str, 
        subdistrict: int = 0,
        extensions: str = 'all'
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        获取行政区划边界 - 依次尝试所有API
        返回 (result, api_name)
        """
        cache_key = f"boundary_{keywords}_{subdistrict}_{extensions}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        for api_name in self.api_order:
            result = None
            try:
                if api_name == 'amap' and self.amap_key:
                    result = self._query_amap_boundary(keywords, subdistrict, extensions)
                elif api_name == 'baidu' and self.baidu_key:
                    result = self._query_baidu_boundary(keywords, subdistrict, extensions)
                elif api_name == 'tencent' and self.tencent_key:
                    result = self._query_tencent_boundary(keywords)
                elif api_name == 'tianditu' and self.tianditu_key:
                    result = self._query_tianditu_boundary(keywords)
            except Exception as e:
                print(f"[MultiMapAPI] {api_name} API失败: {str(e)}")
                continue
            
            if result and self._has_valid_boundary(result):
                print(f"[MultiMapAPI] {api_name}成功获取: {keywords}")
                self.cache[cache_key] = (result, api_name)
                return result, api_name
        
        return None, None
    
    # ==================== 高德地图 (Amap) ====================
    
    def _query_amap_boundary(
        self, keywords: str, subdistrict: int, extensions: str
    ) -> Optional[Dict[str, Any]]:
        try:
            encoded = urllib.parse.quote(keywords)
            url = (
                f"https://restapi.amap.com/v3/config/district?"
                f"key={self.amap_key}&keywords={encoded}"
                f"&subdistrict={subdistrict}&extensions={extensions}"
            )
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == '1' and data.get('districts'):
                    return data['districts'][0]
        except Exception as e:
            print(f"[MultiMapAPI] 高德查询失败: {e}")
        return None
    
    # ==================== 百度地图 (Baidu) ====================
    
    def _query_baidu_boundary(
        self, keywords: str, subdistrict: int, extensions: str
    ) -> Optional[Dict[str, Any]]:
        try:
            encoded = urllib.parse.quote(keywords)
            url = (
                f"https://api.map.baidu.com/api_region_search/v1/?"
                f"ak={self.baidu_key}&keyword={encoded}"
                f"&sub_admin={subdistrict}&extensions_code=1"
            )
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == 0 and data.get('result'):
                    return self._convert_baidu_to_amap_format(data['result'][0])
        except Exception as e:
            print(f"[MultiMapAPI] 百度查询失败: {e}")
        return None
    
    def _convert_baidu_to_amap_format(self, baidu_result: Dict) -> Dict:
        result = {'name': baidu_result.get('name', ''), 'center': '', 'polyline': ''}
        if 'center' in baidu_result:
            lng = baidu_result['center'].get('lng', 0)
            lat = baidu_result['center'].get('lat', 0)
            result['center'] = f"{lng},{lat}"
        if 'boundary' in baidu_result:
            result['polyline'] = baidu_result['boundary']
        return result
    
    # ==================== 腾讯地图 (Tencent) — 修复为行政区划接口 ====================
    
    def _query_tencent_boundary(self, keywords: str) -> Optional[Dict[str, Any]]:
        """
        腾讯地图行政区划API — 获取完整边界polygon数据
        https://apis.map.qq.com/ws/district/v1/search
        """
        try:
            encoded = urllib.parse.quote(keywords)
            url = (
                f"https://apis.map.qq.com/ws/district/v1/search?"
                f"keyword={encoded}&key={self.tencent_key}&get_polygon=2&max_offset=1000"
            )
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == 0 and data.get('result'):
                    return self._convert_tencent_to_amap_format(data['result'])
        except Exception as e:
            print(f"[MultiMapAPI] 腾讯查询失败: {e}")
        return None
    
    def _convert_tencent_to_amap_format(self, tencent_result: Dict) -> Dict:
        """将腾讯行政区划API结果转换为高德格式"""
        result = {'name': '', 'center': '', 'polyline': ''}
        
        # tencent格式: result.data = [[{id, name, fullname, location: {lat,lng}, polygon: [[lng,lat],...]}, ...]]
        rows = tencent_result.get('data', [])
        if not rows or len(rows) == 0:
            return None
        
        first_row = rows[0] if isinstance(rows[0], list) else rows
        first_item = first_row[0] if isinstance(first_row, list) else first_row
        if not first_item:
            return None
        
        result['name'] = first_item.get('fullname', first_item.get('name', ''))
        result['adcode'] = str(first_item.get('id', ''))
        
        loc = first_item.get('location', {})
        if loc:
            result['center'] = f"{loc.get('lng', '')},{loc.get('lat', '')}"
        
        # 腾讯polygon格式: [[lng,lat],[lng,lat],...]  → 高德polyline: lng,lat;lng,lat;...
        polygon = first_item.get('polygon', [])
        if polygon:
            if isinstance(polygon[0], list) and isinstance(polygon[0][0], (int, float)):
                pts = [f"{p[0]},{p[1]}" for p in polygon]
                result['polyline'] = ';'.join(pts)
            elif isinstance(polygon[0], list) and isinstance(polygon[0][0], list):
                rings = []
                for ring in polygon:
                    pts = [f"{p[0]},{p[1]}" for p in ring]
                    rings.append(';'.join(pts))
                result['polyline'] = '|'.join(rings)
        
        return result
    
    # ==================== 天地图 (Tianditu) — 国家测绘局官方API ====================
    
    def _query_tianditu_boundary(self, keywords: str) -> Optional[Dict[str, Any]]:
        """
        天地图行政区划查询API
        POST https://api.tianditu.gov.cn/administrative
        """
        try:
            post_data = json.dumps({
                "searchWord": keywords,
                "searchType": "1",
                "needPolygon": True,
                "needPre": False
            })
            encoded_data = urllib.parse.quote(post_data)
            url = (
                f"https://api.tianditu.gov.cn/administrative?"
                f"postStr={encoded_data}&type=query&tk={self.tianditu_key}"
            )
            
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return self._convert_tianditu_to_amap_format(data)
        except Exception as e:
            print(f"[MultiMapAPI] 天地图查询失败: {e}")
        
        return None
    
    def _convert_tianditu_to_amap_format(self, td_data: Dict) -> Dict:
        """将天地图结果转换为高德格式"""
        result = {'name': '', 'center': '', 'polyline': ''}
        
        if td_data.get('status') != '0':
            return None
        
        info = td_data.get('data', {})
        if not info:
            return None
        
        result['name'] = info.get('key', '')
        lng = info.get('adminLng', 0)
        lat = info.get('adminLat', 0)
        result['center'] = f"{lng},{lat}"
        
        # 天地图polygon格式: GeoJSON MultiPolygon coordinates
        polygon_data = info.get('polygon', {})
        if polygon_data and 'coordinates' in polygon_data:
            coords = polygon_data['coordinates']
            rings = []
            for multipoly_coords in coords:
                for ring_coords in multipoly_coords:
                    pts = [f"{p[0]},{p[1]}" for p in ring_coords]
                    rings.append(';'.join(pts))
            if rings:
                result['polyline'] = '|'.join(rings)
        
        return result
    
    # ==================== 辅助方法 ====================
    
    def _has_valid_boundary(self, district: Dict[str, Any]) -> bool:
        if 'polyline' in district and district['polyline']:
            return True
        if 'districts' in district and district['districts']:
            for sub in district['districts']:
                if 'polyline' in sub and sub['polyline']:
                    return True
        return False
    
    def parse_polyline(self, polyline_str: str) -> list:
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
    
    def try_all_apis_for_polyline(self, district_name: str) -> Optional[str]:
        """专门用于获取polyline — 尝试所有API直到拿到有效polyline"""
        result, source = self.get_administrative_boundary(district_name, 0, 'all')
        if result and result.get('polyline'):
            print(f"[MultiMapAPI] 获取到polyline: {district_name} ({source})")
            return result['polyline']
        
        # 简化关键词再试
        simplified = district_name
        for suffix in ['市', '区', '县', '省', '自治区', '特别行政区', '街道', '镇', '乡']:
            if simplified.endswith(suffix) and len(simplified) > len(suffix):
                simplified = simplified[:-len(suffix)]
        
        if simplified != district_name:
            result, source = self.get_administrative_boundary(simplified, 0, 'all')
            if result and result.get('polyline'):
                print(f"[MultiMapAPI] 简化关键词获取到polyline: {district_name} -> {simplified} ({source})")
                return result['polyline']
        
        return None


_multi_map_api: Optional[MultiMapAPI] = None


def get_multi_map_api(
    amap_key=None, baidu_key=None, tencent_key=None, tianditu_key=None
) -> MultiMapAPI:
    global _multi_map_api
    if _multi_map_api is None:
        _multi_map_api = MultiMapAPI(amap_key, baidu_key, tencent_key, tianditu_key)
    return _multi_map_api