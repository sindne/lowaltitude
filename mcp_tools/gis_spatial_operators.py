import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
@dataclass
class Point:
    lng: float
    lat: float
    def to_list(self) -> List[float]:
        return [self.lng, self.lat]
    @classmethod
    def from_list(cls, coords: List[float]) -> 'Point':
        return cls(lng=coords[0], lat=coords[1])
@dataclass
class Polygon:
    coordinates: List[List[float]]
    def to_list(self) -> List[List[float]]:
        return self.coordinates
    @classmethod
    def from_list(cls, coords: List[List[float]]) -> 'Polygon':
        return cls(coordinates=coords)
class GISSpatialOperators:
    def __init__(self):
        self.earth_radius = 6371.0
    def calculate_haversine_distance(self, point1: Point, point2: Point) -> float:
        lat1_rad = math.radians(point1.lat)
        lat2_rad = math.radians(point2.lat)
        delta_lat = math.radians(point2.lat - point1.lat)
        delta_lng = math.radians(point2.lng - point1.lng)
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return self.earth_radius * c
    def point_in_polygon_ray_casting(self, point: Point, polygon: Polygon) -> bool:
        x, y = (point.lng, point.lat)
        inside = False
        coords = polygon.coordinates
        n = len(coords)
        for i in range(n):
            j = (i + 1) % n
            xi, yi = coords[i]
            xj, yj = coords[j]
            if (yi > y) != (yj > y):
                x_intersect = (y - yi) * (xj - xi) / (yj - yi) + xi
                if x < x_intersect:
                    inside = not inside
        return inside
    def calculate_polygon_area(self, polygon: Polygon) -> float:
        coords = polygon.coordinates
        n = len(coords)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            lng1, lat1 = coords[i]
            lng2, lat2 = coords[j]
            area += lng1 * lat2 - lng2 * lat1
        area = abs(area) / 2.0
        lat_avg = sum((coord[1] for coord in coords)) / n
        km_per_degree_lng = 111.32 * math.cos(math.radians(lat_avg))
        km_per_degree_lat = 110.574
        return area * km_per_degree_lng * km_per_degree_lat
    def calculate_polygon_centroid(self, polygon: Polygon) -> Point:
        coords = polygon.coordinates
        n = len(coords)
        if n == 0:
            return Point(0.0, 0.0)
        avg_lng = sum((coord[0] for coord in coords)) / n
        avg_lat = sum((coord[1] for coord in coords)) / n
        return Point(avg_lng, avg_lat)
    def calculate_bounding_box(self, polygon: Polygon) -> Dict[str, float]:
        coords = polygon.coordinates
        lngs = [coord[0] for coord in coords]
        lats = [coord[1] for coord in coords]
        return {'min_lng': min(lngs), 'max_lng': max(lngs), 'min_lat': min(lats), 'max_lat': max(lats)}
    def buffer_point(self, point: Point, radius_km: float, num_points: int = 32) -> Polygon:
        coordinates = []
        km_per_degree_lng = 111.32 * math.cos(math.radians(point.lat))
        km_per_degree_lat = 110.574
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            delta_lng = radius_km * math.cos(angle) / km_per_degree_lng
            delta_lat = radius_km * math.sin(angle) / km_per_degree_lat
            coordinates.append([point.lng + delta_lng, point.lat + delta_lat])
        coordinates.append(coordinates[0])
        return Polygon(coordinates=coordinates)
    def analyze_spatial_relationship(self, point: Point, polygon: Polygon, distance_threshold_km: float = 5.0) -> Dict[str, Any]:
        centroid = self.calculate_polygon_centroid(polygon)
        distance_to_centroid = self.calculate_haversine_distance(point, centroid)
        inside = self.point_in_polygon_ray_casting(point, polygon)
        area = self.calculate_polygon_area(polygon)
        bbox = self.calculate_bounding_box(polygon)
        risk_level = '低风险'
        if inside:
            risk_level = '高风险'
        elif distance_to_centroid < distance_threshold_km:
            risk_level = '中等风险'
        return {'point': point.to_list(), 'inside_polygon': inside, 'distance_to_centroid_km': round(distance_to_centroid, 2), 'polygon_area_km2': round(area, 2), 'polygon_centroid': centroid.to_list(), 'bounding_box': bbox, 'spatial_risk_level': risk_level, 'analysis_timestamp': None}
    def analyze_multiple_points(self, points: List[Point], polygon: Polygon, distance_threshold_km: float = 5.0) -> List[Dict[str, Any]]:
        results = []
        for point in points:
            result = self.analyze_spatial_relationship(point, polygon, distance_threshold_km)
            results.append(result)
        return results
_gis_spatial_instance = None
def get_gis_spatial_operators() -> GISSpatialOperators:
    global _gis_spatial_instance
    if _gis_spatial_instance is None:
        _gis_spatial_instance = GISSpatialOperators()
    return _gis_spatial_instance
