import os
import json
from typing import List, Dict, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class SHPReader:
    def __init__(self, shp_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.shp_dir = shp_dir if shp_dir else os.path.join(base_dir, 'data', 'collected', 'shp')
        self.shp_file = os.path.join(self.shp_dir, 'shi2022.shp')
        self.data_cache = {}
        self.name_mapping = {}
        self._load_data()

    def _load_data(self):
        try:
            import geopandas as gpd
            encodings = ['GBK', 'GB2312', 'GB18030', 'utf-8', 'latin1']
            gdf = None
            for encoding in encodings:
                try:
                    print(f'[SHPReader] 尝试编码: {encoding}')
                    gdf = gpd.read_file(self.shp_file, encoding=encoding)
                    print(f'[SHPReader] 使用编码 {encoding} 成功')
                    break
                except Exception as e:
                    print(f'[SHPReader] 编码 {encoding} 失败: {e}')
                    continue
            if gdf is not None:
                self._process_geopandas_data(gdf)
                print(f'[SHPReader] geopandas 加载成功,共 {len(self.data_cache)} 条记录')
                return
        except ImportError:
            print(f'[SHPReader] geopandas 未安装,尝试其他方法')
        except Exception as e:
            print(f'[SHPReader] geopandas 加载失败: {e}')

        try:
            import shapefile
            print(f'[SHPReader] 使用shapefile库加载...')
            encodings = ['GBK', 'GB2312', 'GB18030', 'utf-8', 'latin1']
            sf = None
            for encoding in encodings:
                try:
                    print(f'[SHPReader] 尝试编码: {encoding}')
                    sf = shapefile.Reader(self.shp_file, encoding=encoding)
                    print(f'[SHPReader] 使用编码 {encoding} 成功')
                    break
                except Exception as e:
                    print(f'[SHPReader] 编码 {encoding} 失败: {e}')
                    continue
            if sf is not None:
                self._process_shapefile_data(sf)
                print(f'[SHPReader] shapefile库加载成功,共 {len(self.data_cache)} 条记录')
                return
        except ImportError:
            print(f'[SHPReader] shapefile库未安装')
        except Exception as e:
            print(f'[SHPReader] shapefile库加载失败: {e}')

        try:
            import fiona
            print(f'[SHPReader] 使用fiona加载...')
            encodings = ['GBK', 'GB2312', 'GB18030', 'utf-8', 'latin1']
            for encoding in encodings:
                try:
                    print(f'[SHPReader] 尝试编码: {encoding}')
                    with fiona.open(self.shp_file, 'r', encoding=encoding) as src:
                        self._process_fiona_data(src)
                        print(f'[SHPReader] 使用编码 {encoding} 成功')
                        print(f'[SHPReader] fiona加载成功,共 {len(self.data_cache)} 条记录')
                        return
                except Exception as e:
                    print(f'[SHPReader] 编码 {encoding} 失败: {e}')
                    continue
        except ImportError:
            print(f'[SHPReader] fiona未安装')
        except Exception as e:
            print(f'[SHPReader] fiona加载失败: {e}')

        try:
            print(f'[SHPReader] 尝试简化方法(只读取几何数据)...')
            self._try_simple_geometry_load()
        except Exception as e:
            print(f'[SHPReader] 所有方法都失败,SHP数据不可用')
            print(f'[SHPReader] 初始化失败: {e}')
            import traceback
            traceback.print_exc()

    def _process_geopandas_data(self, gdf):
        for idx, row in gdf.iterrows():
            name = None
            for field in gdf.columns:
                if field == 'geometry':
                    continue
                val = row[field]
                if val and isinstance(val, str) and len(val) >= 2:
                    name = val
                    break
            if not name:
                continue
            geometry = row.geometry
            if geometry is None:
                continue
            coords = self._extract_coords_from_geometry(geometry)
            self.data_cache[name] = {
                'name': name,
                'coordinates': coords,
                'center': self._calculate_center(coords)
            }
            simple_name = self._simplify_name(name)
            self.name_mapping[simple_name] = name

    def _process_shapefile_data(self, sf):
        fields = [f[0] for f in sf.fields[1:]]
        for shape_record in sf.shapeRecords():
            record = shape_record.record
            shape = shape_record.shape
            name = None
            for field in fields:
                idx = fields.index(field)
                val = record[idx]
                if val and isinstance(val, str) and len(val) >= 2:
                    name = val
                    break
            if not name:
                continue
            coords = self._extract_coords_from_shape(shape)
            self.data_cache[name] = {
                'name': name,
                'coordinates': coords,
                'center': self._calculate_center(coords)
            }
            simple_name = self._simplify_name(name)
            self.name_mapping[simple_name] = name

    def _process_fiona_data(self, src):
        for feature in src:
            props = feature.get('properties', {})
            geom = feature.get('geometry')
            name = None
            for field, val in props.items():
                if val and isinstance(val, str) and len(val) >= 2:
                    name = val
                    break
            if not name:
                continue
            coords = self._extract_coords_from_geojson(geom)
            self.data_cache[name] = {
                'name': name,
                'coordinates': coords,
                'center': self._calculate_center(coords)
            }
            simple_name = self._simplify_name(name)
            self.name_mapping[simple_name] = name

    def _extract_coords_from_geometry(self, geometry):
        coords = []
        try:
            if geometry.geom_type == 'Polygon':
                for ring in geometry.geoms if hasattr(geometry, 'geoms') else [geometry]:
                    ring_coords = []
                    for point in ring.exterior.coords:
                        ring_coords.append([float(point[0]), float(point[1])])
                    coords.append(ring_coords)
            elif geometry.geom_type == 'MultiPolygon':
                for poly in geometry.geoms:
                    ring_coords = []
                    for point in poly.exterior.coords:
                        ring_coords.append([float(point[0]), float(point[1])])
                    coords.append(ring_coords)
        except Exception as e:
            print(f'[SHPReader] 提取坐标失败: {e}')
        return coords

    def _extract_coords_from_shape(self, shape):
        coords = []
        try:
            parts = shape.parts if hasattr(shape, 'parts') else [0]
            points = shape.points
            for i in range(len(parts)):
                start_idx = parts[i]
                end_idx = parts[i + 1] if i + 1 < len(parts) else len(points)
                ring_coords = []
                for j in range(start_idx, end_idx):
                    ring_coords.append([float(points[j][0]), float(points[j][1])])
                coords.append(ring_coords)
        except Exception as e:
            print(f'[SHPReader] 提取shape坐标失败: {e}')
        return coords

    def _extract_coords_from_geojson(self, geom):
        coords = []
        try:
            geom_type = geom.get('type')
            geom_coords = geom.get('coordinates', [])
            if geom_type == 'Polygon':
                for ring in geom_coords:
                    ring_coords = [[float(p[0]), float(p[1])] for p in ring]
                    coords.append(ring_coords)
            elif geom_type == 'MultiPolygon':
                for polygon in geom_coords:
                    for ring in polygon:
                        ring_coords = [[float(p[0]), float(p[1])] for p in ring]
                        coords.append(ring_coords)
        except Exception as e:
            print(f'[SHPReader] 提取GeoJSON坐标失败: {e}')
        return coords

    def _calculate_center(self, coords: List[List[List[float]]]) -> Tuple[float, float]:
        all_points = []
        for ring in coords:
            all_points.extend(ring)
        lng_sum = sum(p[0] for p in all_points)
        lat_sum = sum(p[1] for p in all_points)
        count = len(all_points)
        return (lng_sum / count, lat_sum / count)

    def _simplify_name(self, name: str) -> str:
        suffixes = ['市', '区', '县', '省', '自治区', '特别行政区', '自治州', '盟', '地区']
        result = name
        for suffix in suffixes:
            if result.endswith(suffix):
                result = result[:-len(suffix)]
        return result

    def get_boundary(self, name: str) -> Optional[Dict[str, Any]]:
        simple_name = self._simplify_name(name)
        original_name = self.name_mapping.get(simple_name)
        if original_name:
            return self.data_cache.get(original_name)
        return None

    def to_amap_format(self, name: str) -> Optional[Dict[str, Any]]:
        boundary = self.get_boundary(name)
        if not boundary:
            return None
        polyline_parts = []
        for ring in boundary['coordinates']:
            ring_str = ';'.join([f'{lng},{lat}' for lng, lat in ring])
            polyline_parts.append(ring_str)
        polyline = '|'.join(polyline_parts)
        return {
            'name': boundary['name'],
            'center': f"{boundary['center'][0]},{boundary['center'][1]}",
            'polyline': polyline,
            'level': 'city'
        }

    def _try_simple_geometry_load(self):
        import geopandas as gpd
        encodings = ['GBK', 'GB2312', 'GB18030', 'utf-8', 'latin1']
        gdf = None
        for encoding in encodings:
            try:
                gdf = gpd.read_file(self.shp_file, encoding=encoding, ignore_fields=True)
                break
            except Exception as e:
                print(f'[SHPReader] 简化编码 {encoding} 失败: {e}')
                continue
        if gdf is None:
            raise Exception('简化geopandas 加载失败')
        for idx, row in gdf.iterrows():
            geometry = row.geometry
            if geometry is None:
                continue
            coords = self._extract_coords_from_geometry(geometry)
            name = f'区域_{idx + 1}'
            self.data_cache[name] = {
                'name': name,
                'coordinates': coords,
                'center': self._calculate_center(coords)
            }
        print(f'[SHPReader] 简化加载成功,共 {len(self.data_cache)} 条记录')

    def is_available(self) -> bool:
        return os.path.exists(self.shp_file) and len(self.data_cache) > 0

_shp_reader: Optional[SHPReader] = None

def get_shp_reader(shp_dir: Optional[str] = None) -> SHPReader:
    global _shp_reader
    if _shp_reader is None:
        _shp_reader = SHPReader(shp_dir)
    return _shp_reader
