import os
import struct
from typing import List, Dict, Any, Optional, Tuple

class CustomSHPReader:
    def __init__(self, shp_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.shp_dir = shp_dir if shp_dir else os.path.join(base_dir, 'data', 'collected', 'shp')
        self.shp_file = os.path.join(self.shp_dir, 'shi2022.shp')
        self.dbf_file = os.path.join(self.shp_dir, 'shi2022.dbf')
        self.shx_file = os.path.join(self.shp_dir, 'shi2022.shx')
        self.data_cache = {}
        self.name_mapping = {}
        self._load_data()

    def _load_data(self):
        try:
            records = self._read_dbf()
            geometries = self._read_shp()
            min_count = min(len(records), len(geometries))
            for i in range(min_count):
                record = records[i]
                geometry = geometries[i]
                city_name = record.get('市', '')
                if not city_name:
                    continue
                coords = self._extract_polygon_coords(geometry)
                self.data_cache[city_name] = {
                    'name': city_name,
                    'province': record.get('省', ''),
                    'city_code': record.get('市代码', ''),
                    'area': record.get('面积', 0),
                    'coordinates': coords,
                    'center': self._calculate_center(coords)
                }
                simple_name = self._simplify_name(city_name)
                self.name_mapping[simple_name] = city_name
            print(f'[CustomSHPReader] 成功加载 {len(self.data_cache)} 个城市边界数据')
        except Exception as e:
            print(f'[CustomSHPReader] 加载失败: {e}')
            import traceback
            traceback.print_exc()

    def _read_dbf(self) -> List[Dict[str, Any]]:
        records = []
        with open(self.dbf_file, 'rb') as f:
            header = f.read(32)
            num_records = struct.unpack('<I', header[4:8])[0]
            header_len = struct.unpack('<H', header[8:10])[0]
            record_len = struct.unpack('<H', header[10:12])[0]
            fields = []
            f.seek(32)
            while True:
                field_info = f.read(32)
                if field_info[0] == 13:
                    break
                field_name = field_info[0:11].split(b'\x00')[0].decode('gbk', errors='ignore')
                field_type = chr(field_info[11])
                field_len = field_info[16]
                fields.append({'name': field_name, 'type': field_type, 'length': field_len})
            f.seek(header_len)
            for _ in range(num_records):
                record = f.read(record_len)
                record_data = {}
                offset = 1
                for field in fields:
                    field_data = record[offset:offset + field['length']]
                    offset += field['length']
                    value = field_data.decode('gbk', errors='ignore').strip()
                    if field['type'] == 'N':
                        try:
                            value = float(value)
                            if value.is_integer():
                                value = int(value)
                        except:
                            pass
                    elif field['type'] == 'F':
                        try:
                            value = float(value)
                        except:
                            pass
                    record_data[field['name']] = value
                records.append(record_data)
        return records

    def _read_shp(self) -> List[Dict[str, Any]]:
        geometries = []
        with open(self.shp_file, 'rb') as f:
            header = f.read(100)
            file_length = struct.unpack('>I', header[24:28])[0] * 2
            version = struct.unpack('<I', header[28:32])[0]
            shape_type = struct.unpack('<I', header[32:36])[0]
            while True:
                rec_header = f.read(8)
                if len(rec_header) < 8:
                    break
                rec_number = struct.unpack('>I', rec_header[0:4])[0]
                rec_length = struct.unpack('>I', rec_header[4:8])[0] * 2
                rec_content = f.read(rec_length)
                if len(rec_content) < rec_length:
                    break
                geom_shape_type = struct.unpack('<I', rec_content[0:4])[0]
                if geom_shape_type == 5:
                    x_min = struct.unpack('<d', rec_content[4:12])[0]
                    y_min = struct.unpack('<d', rec_content[12:20])[0]
                    x_max = struct.unpack('<d', rec_content[20:28])[0]
                    y_max = struct.unpack('<d', rec_content[28:36])[0]
                    num_parts = struct.unpack('<I', rec_content[36:40])[0]
                    num_points = struct.unpack('<I', rec_content[40:44])[0]
                    parts = []
                    offset = 44
                    for _ in range(num_parts):
                        part_idx = struct.unpack('<I', rec_content[offset:offset + 4])[0]
                        parts.append(part_idx)
                        offset += 4
                    points = []
                    for _ in range(num_points):
                        x = struct.unpack('<d', rec_content[offset:offset + 8])[0]
                        y = struct.unpack('<d', rec_content[offset + 8:offset + 16])[0]
                        points.append([x, y])
                        offset += 16
                    geometries.append({'type': 'Polygon', 'parts': parts, 'points': points})
        return geometries

    def _extract_polygon_coords(self, geometry: Dict[str, Any]) -> List[List[List[float]]]:
        coords = []
        if geometry.get('type') != 'Polygon':
            return coords
        points = geometry.get('points', [])
        parts = geometry.get('parts', [0])
        for i in range(len(parts)):
            start_idx = parts[i]
            end_idx = parts[i + 1] if i + 1 < len(parts) else len(points)
            ring_coords = []
            for j in range(start_idx, end_idx):
                ring_coords.append([points[j][0], points[j][1]])
            coords.append(ring_coords)
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

    def is_available(self) -> bool:
        return os.path.exists(self.shp_file) and os.path.exists(self.dbf_file)

_custom_shp_reader: Optional[CustomSHPReader] = None

def get_custom_shp_reader(shp_dir: Optional[str] = None) -> CustomSHPReader:
    global _custom_shp_reader
    if _custom_shp_reader is None:
        _custom_shp_reader = CustomSHPReader(shp_dir)
    return _custom_shp_reader
