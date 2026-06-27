import os
import json
import psycopg2
from psycopg2 import sql, extras
from psycopg2.extras import Json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

class PostGISDatabase:
    def __init__(self,
                 host: str = 'localhost',
                 port: int = 5432,
                 database: str = 'postgres',
                 user: str = 'postgres',
                 password: str = '035548'):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn = None
        self._connect()
        self._initialize_tables()

    def _connect(self):
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.conn.autocommit = True
            print("[PostGIS] 数据库连接成功")
            self._enable_postgis()
        except Exception as e:
            print(f"[PostGIS] 数据库连接失败: {e}")
            raise

    def _enable_postgis(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
                print("[PostGIS] PostGIS扩展已启用")
        except Exception as e:
            print(f"[PostGIS] 启用PostGIS扩展失败: {e}")

    def _initialize_tables(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""CREATE TABLE IF NOT EXISTS cities (
                    id SERIAL PRIMARY KEY, name VARCHAR(100) UNIQUE NOT NULL,
                    province VARCHAR(50), center GEOGRAPHY(POINT,4326),
                    boundary GEOGRAPHY(MULTIPOLYGON,4326), population_density FLOAT,
                    gdp FLOAT, area FLOAT, city_code VARCHAR(20),
                    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS infrastructure (
                    id SERIAL PRIMARY KEY, city_id INTEGER REFERENCES cities(id),
                    name VARCHAR(200) NOT NULL, infra_type VARCHAR(50) NOT NULL,
                    location GEOGRAPHY(POINT,4326), description TEXT, source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS sensitive_areas (
                    id SERIAL PRIMARY KEY, city_id INTEGER REFERENCES cities(id),
                    name VARCHAR(200) NOT NULL, area_type VARCHAR(50) NOT NULL,
                    location GEOGRAPHY(POINT,4326), priority INTEGER DEFAULT 1,
                    description TEXT, source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS assessment_history (
                    id SERIAL PRIMARY KEY, region VARCHAR(100) NOT NULL,
                    risk_level VARCHAR(20), risk_score FLOAT,
                    risk_data JSONB, user_input TEXT,
                    created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS risk_areas (
                    id SERIAL PRIMARY KEY, assessment_id INTEGER REFERENCES assessment_history(id),
                    name VARCHAR(200), level VARCHAR(20),
                    polygon GEOGRAPHY(POLYGON,4326), explanation TEXT,
                    key_factors JSONB, created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS knowledge_graphs (
                    id SERIAL PRIMARY KEY, city_name VARCHAR(100) NOT NULL,
                    region_name VARCHAR(100), entities JSONB, relations JSONB,
                    metadata JSONB, created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(city_name, region_name));""")
                cur.execute("""CREATE TABLE IF NOT EXISTS city_elevations (
                    id SERIAL PRIMARY KEY, city_name VARCHAR(100) UNIQUE NOT NULL,
                    avg_elevation FLOAT, min_elevation FLOAT, max_elevation FLOAT,
                    source VARCHAR(50), created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS landmark_buildings (
                    id SERIAL PRIMARY KEY, city_id INTEGER REFERENCES cities(id),
                    city_name VARCHAR(100), name VARCHAR(200) NOT NULL,
                    height FLOAT, floors INTEGER, location GEOGRAPHY(POINT,4326),
                    description TEXT, source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS terrain_cache (
                    id SERIAL PRIMARY KEY, lng FLOAT NOT NULL, lat FLOAT NOT NULL,
                    elevation FLOAT, accuracy VARCHAR(20), source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(lng, lat));""")
                cur.execute("""CREATE TABLE IF NOT EXISTS wind_cache (
                    id SERIAL PRIMARY KEY, city_name VARCHAR(100) NOT NULL,
                    wind_speed FLOAT, wind_direction FLOAT, wind_level INTEGER,
                    weather VARCHAR(50), lng FLOAT, lat FLOAT, source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS building_cache (
                    id SERIAL PRIMARY KEY, lng FLOAT NOT NULL, lat FLOAT NOT NULL,
                    height FLOAT, name VARCHAR(200), confidence VARCHAR(20),
                    source VARCHAR(50), created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(lng, lat));""")
                cur.execute("""CREATE TABLE IF NOT EXISTS district_boundaries (
                    id SERIAL PRIMARY KEY, city_name VARCHAR(100) NOT NULL,
                    district_name VARCHAR(100) NOT NULL, polyline TEXT,
                    center_lng FLOAT, center_lat FLOAT, adcode VARCHAR(20),
                    boundary GEOGRAPHY(MULTIPOLYGON,4326), source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(city_name, district_name));""")
                cur.execute("""CREATE TABLE IF NOT EXISTS training_datasets (
                    id SERIAL PRIMARY KEY, name VARCHAR(200) UNIQUE NOT NULL,
                    dataset_type VARCHAR(50) DEFAULT 'risk_assessment',
                    total_samples INTEGER DEFAULT 0, base_model VARCHAR(100),
                    metadata JSONB, created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS training_samples (
                    id SERIAL PRIMARY KEY, dataset_id INTEGER REFERENCES training_datasets(id),
                    sample_id VARCHAR(200), sample_type VARCHAR(50) DEFAULT 'risk_assessment',
                    region VARCHAR(100), risk_level VARCHAR(20),
                    messages JSONB, content JSONB, quality_score FLOAT DEFAULT 0.5,
                    source VARCHAR(50) DEFAULT 'generated',
                    created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("""CREATE TABLE IF NOT EXISTS model_finetune_history (
                    id SERIAL PRIMARY KEY, model_name VARCHAR(100) NOT NULL,
                    model_path VARCHAR(500), dataset_id INTEGER REFERENCES training_datasets(id),
                    base_model VARCHAR(100), lora_config JSONB, training_args JSONB,
                    training_samples_count INTEGER DEFAULT 0, status VARCHAR(50) DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT NOW());""")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_cities_name ON cities(name);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_infrastructure_city ON infrastructure(city_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_sensitive_areas_city ON sensitive_areas(city_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_assessment_region ON assessment_history(region);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_assessment_created ON assessment_history(created_at);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_areas_assessment ON risk_areas(assessment_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_kg_city ON knowledge_graphs(city_name);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_training_datasets_name ON training_datasets(name);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_training_samples_dataset ON training_samples(dataset_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_finetune_history_model ON model_finetune_history(model_name);")
                print("[PostGIS] 数据库表结构初始化完成")
        except Exception as e:
            print(f"[PostGIS] 初始化表结构失败: {e}")
            self.conn.rollback()

    def add_city(self, name: str, province: str = None,
                 center_lng: float = None, center_lat: float = None,
                 population_density: float = None, gdp: float = None,
                 area: float = None, city_code: str = None,
                 boundary_coords: List = None) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT id FROM cities WHERE name = %s;", (name,))
                existing = cur.fetchone()
                center_point = None
                if center_lng and center_lat:
                    cur.execute("SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326);", (center_lng, center_lat))
                    center_point = cur.fetchone()[0]
                boundary = None
                if boundary_coords:
                    try:
                        wkt = self._coords_to_wkt(boundary_coords)
                        cur.execute("SELECT ST_SetSRID(ST_GeomFromText(%s), 4326);", (wkt,))
                        boundary = cur.fetchone()[0]
                    except Exception as e:
                        print(f"[PostGIS] 边界数据转换失败: {e}")
                if existing:
                    cur.execute("""
                        UPDATE cities SET province = COALESCE(%s, province),
                            center = COALESCE(%s, center), boundary = COALESCE(%s, boundary),
                            population_density = COALESCE(%s, population_density),
                            gdp = COALESCE(%s, gdp), area = COALESCE(%s, area),
                            city_code = COALESCE(%s, city_code), updated_at = NOW()
                        WHERE id = %s RETURNING id;
                    """, (province, center_point, boundary, population_density, gdp, area, city_code, existing[0]))
                    return cur.fetchone()[0]
                else:
                    cur.execute("""
                        INSERT INTO cities (name, province, center, boundary, population_density, gdp, area, city_code)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                    """, (name, province, center_point, boundary, population_density, gdp, area, city_code))
                    return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加城市失败: {e}")
            return None

    def _coords_to_wkt(self, coords: List) -> str:
        if not coords:
            return None
        polygons = []
        for ring in coords:
            points = []
            for point in ring:
                if len(point) >= 2:
                    points.append(f"{point[0]} {point[1]}")
            if points:
                polygons.append(f"({', '.join(points)})")
        if polygons:
            return f"MULTIPOLYGON(({', '.join(polygons)}))"
        return None

    def get_city(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM cities WHERE name = %s;", (name,))
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            print(f"[PostGIS] 获取城市失败: {e}")
            return None

    def add_infrastructure(self, city_id: int, name: str, infra_type: str,
                           lng: float = None, lat: float = None,
                           description: str = None, source: str = None) -> int:
        try:
            with self.conn.cursor() as cur:
                if isinstance(city_id, str):
                    city = self.get_city(city_id)
                    if city:
                        city_id = city['id']
                    else:
                        city_id = self.add_city(city_id)
                        if not city_id:
                            return None
                location = None
                if lng is not None and lat is not None:
                    cur.execute("SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326);", (lng, lat))
                    location = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO infrastructure (city_id, name, infra_type, location, description, source)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
                """, (city_id, name, infra_type, location, description, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加基础设施失败: {e}")
            return None

    def get_infrastructure(self, city_name: str) -> List[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""SELECT i.* FROM infrastructure i
                    JOIN cities c ON i.city_id = c.id WHERE c.name = %s;""", (city_name,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[PostGIS] 获取基础设施失败: {e}")
            return []

    def add_sensitive_area(self, city_id: int, name: str, area_type: str,
                           lng: float = None, lat: float = None,
                           priority: int = 1, description: str = None,
                           source: str = None) -> int:
        try:
            with self.conn.cursor() as cur:
                if isinstance(city_id, str):
                    city = self.get_city(city_id)
                    if city:
                        city_id = city['id']
                    else:
                        city_id = self.add_city(city_id)
                        if not city_id:
                            return None
                location = None
                if lng is not None and lat is not None:
                    cur.execute("SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326);", (lng, lat))
                    location = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO sensitive_areas (city_id, name, area_type, location, priority, description, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (city_id, name, area_type, location, priority, description, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加敏感区域失败: {e}")
            return None

    def get_sensitive_areas(self, city_name: str) -> List[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""SELECT s.* FROM sensitive_areas s
                    JOIN cities c ON s.city_id = c.id WHERE c.name = %s;""", (city_name,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[PostGIS] 获取敏感区域失败: {e}")
            return []

    def add_assessment_history(self, region: str, risk_level: str,
                                risk_score: float = None, risk_data: Dict = None,
                                user_input: str = None) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO assessment_history (region, risk_level, risk_score, risk_data, user_input)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id;
                """, (region, risk_level, risk_score, Json(risk_data) if risk_data else None, user_input))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加评估历史失败: {e}")
            return None

    def add_risk_area(self, assessment_id: int, name: str, level: str,
                      coordinates: List = None, explanation: str = None,
                      key_factors: List = None) -> int:
        try:
            with self.conn.cursor() as cur:
                polygon = None
                if coordinates and len(coordinates) >= 3:
                    try:
                        wkt = self._coords_to_single_polygon_wkt(coordinates)
                        cur.execute("SELECT ST_SetSRID(ST_GeomFromText(%s), 4326);", (wkt,))
                        polygon = cur.fetchone()[0]
                    except Exception as e:
                        print(f"[PostGIS] 风险区域几何转换失败: {e}")
                cur.execute("""
                    INSERT INTO risk_areas (assessment_id, name, level, polygon, explanation, key_factors)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
                """, (assessment_id, name, level, polygon, explanation,
                      Json(key_factors) if key_factors else None))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加风险区域失败: {e}")
            return None

    def get_assessment_with_risk_areas(self, assessment_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM assessment_history WHERE id = %s;", (assessment_id,))
                assessment = cur.fetchone()
                if not assessment:
                    return None
                cur.execute("SELECT * FROM risk_areas WHERE assessment_id = %s;", (assessment_id,))
                risk_areas = [dict(row) for row in cur.fetchall()]
                result = dict(assessment)
                result['risk_areas'] = risk_areas
                return result
        except Exception as e:
            print(f"[PostGIS] 获取评估详情失败: {e}")
            return None

    def _coords_to_single_polygon_wkt(self, coords: List) -> Optional[str]:
        if not coords or len(coords) < 3:
            return None
        points = []
        for point in coords:
            if len(point) >= 2:
                points.append(f"{point[0]} {point[1]}")
        if len(points) >= 3:
            if points[0] != points[-1]:
                points.append(points[0])
            return f"POLYGON(({', '.join(points)}))"
        return None

    def get_assessment_history(self, region: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                if region:
                    cur.execute("SELECT * FROM assessment_history WHERE region = %s ORDER BY created_at DESC LIMIT %s;", (region, limit))
                else:
                    cur.execute("SELECT * FROM assessment_history ORDER BY created_at DESC LIMIT %s;", (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[PostGIS] 获取评估历史失败: {e}")
            return []

    def save_knowledge_graph(self, city_name: str, region_name: str = None,
                             entities: List = None, relations: List = None,
                             metadata: Dict = None) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_graphs (city_name, region_name, entities, relations, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (city_name, region_name) DO UPDATE SET
                        entities = EXCLUDED.entities, relations = EXCLUDED.relations,
                        metadata = EXCLUDED.metadata, created_at = NOW()
                    RETURNING id;
                """, (city_name, region_name,
                      Json(entities) if entities else None,
                      Json(relations) if relations else None,
                      Json(metadata) if metadata else None))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 保存知识图谱失败: {e}")
            return None

    def get_knowledge_graph(self, city_name: str, region_name: str = None) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                if region_name:
                    cur.execute("SELECT * FROM knowledge_graphs WHERE city_name = %s AND region_name = %s;", (city_name, region_name))
                else:
                    cur.execute("SELECT * FROM knowledge_graphs WHERE city_name = %s ORDER BY created_at DESC LIMIT 1;", (city_name,))
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            print(f"[PostGIS] 获取知识图谱失败: {e}")
            return None

    def add_city_elevation(self, city_name: str, avg_elevation: float,
                           min_elevation: float = None, max_elevation: float = None,
                           source: str = None) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO city_elevations (city_name, avg_elevation, min_elevation, max_elevation, source)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (city_name) DO UPDATE SET
                        avg_elevation = EXCLUDED.avg_elevation,
                        min_elevation = EXCLUDED.min_elevation,
                        max_elevation = EXCLUDED.max_elevation,
                        source = EXCLUDED.source
                    RETURNING id;
                """, (city_name, avg_elevation, min_elevation, max_elevation, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加城市海拔失败: {e}")
            return None

    def get_city_elevation(self, city_name: str) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM city_elevations WHERE city_name = %s;", (city_name,))
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            print(f"[PostGIS] 获取城市海拔失败: {e}")
            return None

    def add_landmark_building(self, city_id: int, name: str, height: float,
                               lng: float = None, lat: float = None,
                               floors: int = None, description: str = None,
                               source: str = None) -> int:
        try:
            with self.conn.cursor() as cur:
                location = None
                if lng is not None and lat is not None:
                    cur.execute("SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326);", (lng, lat))
                    location = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO landmark_buildings (city_id, name, height, floors, location, description, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (city_id, name, height, floors, location, description, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加地标建筑失败: {e}")
            return None

    def get_landmark_buildings(self, city_name: str) -> List[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""SELECT l.* FROM landmark_buildings l
                    JOIN cities c ON l.city_id = c.id WHERE c.name = %s;""", (city_name,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[PostGIS] 获取地标建筑失败: {e}")
            return []

    def get_landmark_by_name(self, city_name: str, building_name: str) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""SELECT l.* FROM landmark_buildings l
                    JOIN cities c ON l.city_id = c.id
                    WHERE c.name = %s AND l.name = %s;""", (city_name, building_name))
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            print(f"[PostGIS] 获取地标建筑失败: {e}")
            return None

    def add_terrain_cache(self, lng: float, lat: float, elevation: float,
                           accuracy: str = None, source: str = None) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO terrain_cache (lng, lat, elevation, accuracy, source)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (lng, lat) DO UPDATE SET elevation = EXCLUDED.elevation
                    RETURNING id;
                """, (lng, lat, elevation, accuracy, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加地形缓存失败: {e}")
            return None

    def get_terrain_cache(self, lng: float, lat: float) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM terrain_cache WHERE lng = %s AND lat = %s;", (lng, lat))
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            print(f"[PostGIS] 获取地形缓存失败: {e}")
            return None

    def add_wind_cache(self, city_name: str, wind_speed: float,
                        wind_direction: float = None, wind_level: int = None,
                        weather: str = None, lng: float = None, lat: float = None,
                        source: str = None) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO wind_cache (city_name, wind_speed, wind_direction, wind_level, weather, lng, lat, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (city_name, wind_speed, wind_direction, wind_level, weather, lng, lat, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加风场缓存失败: {e}")
            return None

    def get_wind_cache(self, city_name: str, max_age_seconds: int = 3600) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""SELECT * FROM wind_cache WHERE city_name = %s
                    AND created_at > NOW() - INTERVAL '%s seconds'
                    ORDER BY created_at DESC LIMIT 1;""", (city_name, max_age_seconds))
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            print(f"[PostGIS] 获取风场缓存失败: {e}")
            return None

    def add_building_cache(self, lng: float, lat: float, height: float,
                         name: str = None, confidence: str = None,
                         source: str = None) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO building_cache (lng, lat, height, name, confidence, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (lng, lat) DO UPDATE SET height = EXCLUDED.height
                    RETURNING id;
                """, (lng, lat, height, name, confidence, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加建筑缓存失败: {e}")
            return None

    def get_building_cache(self, lng: float, lat: float) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM building_cache WHERE lng = %s AND lat = %s;", (lng, lat))
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            print(f"[PostGIS] 获取建筑缓存失败: {e}")
            return None

    def add_district_boundary(self, city_name: str, district_name: str,
                               polyline: str = None, center_lng: float = None,
                               center_lat: float = None, adcode: str = None,
                               source: str = 'amap') -> int:
        try:
            with self.conn.cursor() as cur:
                boundary_geom = None
                if polyline:
                    coords_list = self._polyline_to_coords_list(polyline)
                    if coords_list:
                        wkt = self._coords_to_wkt(coords_list)
                        if wkt:
                            cur.execute("SELECT ST_SetSRID(ST_GeomFromText(%s), 4326);", (wkt,))
                            boundary_geom = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO district_boundaries (city_name, district_name, polyline, center_lng, center_lat, adcode, boundary, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (city_name, district_name) DO UPDATE SET
                        polyline = EXCLUDED.polyline, boundary = EXCLUDED.boundary,
                        center_lng = EXCLUDED.center_lng, center_lat = EXCLUDED.center_lat
                    RETURNING id;
                """, (city_name, district_name, polyline, center_lng, center_lat, adcode, boundary_geom, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加行政区划边界失败 ({district_name}): {e}")
            return None

    def get_district_boundary(self, city_name: str, district_name: str) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM district_boundaries WHERE city_name = %s AND district_name = %s;", (city_name, district_name))
                result = cur.fetchone()
                if result and result.get('polyline'):
                    return dict(result)
                return None
        except Exception as e:
            print(f"[PostGIS] 获取行政区划边界失败 ({district_name}): {e}")
            return None

    def _polyline_to_coords_list(self, polyline_str: str) -> List:
        if not polyline_str:
            return None
        coords = []
        try:
            for ring in polyline_str.split('|'):
                ring_coords = []
                for pt in ring.split(';'):
                    if ',' in pt:
                        parts = pt.split(',')
                        ring_coords.append([float(parts[0]), float(parts[1])])
                if ring_coords:
                    coords.append(ring_coords)
        except Exception as e:
            print(f"[PostGIS] polyline转换失败: {e}")
            return None
        return coords if coords else None

    def create_training_dataset(self, name: str, dataset_type: str = "risk_assessment",
                                total_samples: int = 0, base_model: str = None,
                                metadata: Dict = None) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT id FROM training_datasets WHERE name = %s", (name,))
                result = cur.fetchone()
                if result:
                    return result[0]
                cur.execute("""
                    INSERT INTO training_datasets (name, dataset_type, total_samples, base_model, metadata)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id;
                """, (name, dataset_type, total_samples, base_model, Json(metadata) if metadata else None))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 创建训练数据集失败: {e}")
            return None

    def add_training_sample(self, dataset_id: int, sample_id: str,
                            sample_type: str = "risk_assessment", region: str = None,
                            risk_level: str = None, messages: List = None,
                            content: Dict = None, quality_score: float = 0.5,
                            source: str = "generated") -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO training_samples (dataset_id, sample_id, sample_type, region, risk_level, messages, content, quality_score, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (dataset_id, sample_id, sample_type, region, risk_level,
                      Json(messages) if messages else None,
                      Json(content) if content else None,
                      quality_score, source))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 添加训练样本失败: {e}")
            return None

    def add_training_samples_batch(self, dataset_id: int, samples: List[Dict[str, Any]]) -> int:
        count = 0
        try:
            with self.conn.cursor() as cur:
                for sample in samples:
                    cur.execute("""
                        INSERT INTO training_samples (dataset_id, sample_id, sample_type, region, risk_level, messages, content, quality_score, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (dataset_id,
                          sample.get("id", sample.get("sample_id", "")),
                          sample.get("type", sample.get("sample_type", "risk_assessment")),
                          sample.get("region", ""),
                          sample.get("risk_level", ""),
                          Json(sample.get("messages")) if sample.get("messages") else None,
                          Json(sample) if not sample.get("messages") else None,
                          sample.get("quality_score", 0.5),
                          sample.get("source", "generated")))
                    count += 1
        except Exception as e:
            print(f"[PostGIS] 批量添加训练样本失败: {e}")
        return count

    def get_training_dataset(self, dataset_id: int = None, name: str = None) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                if dataset_id:
                    cur.execute("SELECT * FROM training_datasets WHERE id = %s;", (dataset_id,))
                elif name:
                    cur.execute("SELECT * FROM training_datasets WHERE name = %s;", (name,))
                else:
                    return None
                result = cur.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"[PostGIS] 获取训练数据集失败: {e}")
            return None

    def get_latest_training_dataset(self, dataset_type: str = None) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                if dataset_type:
                    cur.execute("SELECT * FROM training_datasets WHERE dataset_type = %s ORDER BY created_at DESC LIMIT 1;", (dataset_type,))
                else:
                    cur.execute("SELECT * FROM training_datasets ORDER BY created_at DESC LIMIT 1;")
                result = cur.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"[PostGIS] 获取最新训练数据集失败: {e}")
            return None

    def get_training_samples(self, dataset_id: int, limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                query = "SELECT * FROM training_samples WHERE dataset_id = %s ORDER BY created_at"
                params = [dataset_id]
                if limit is not None:
                    query += " LIMIT %s OFFSET %s"
                    params.extend([limit, offset])
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[PostGIS] 获取训练样本失败: {e}")
            return []

    def export_training_json(self, dataset_id: int, output_path: str = None) -> Optional[str]:
        samples = self.get_training_samples(dataset_id)
        if not samples:
            print(f"[PostGIS] 数据集 {dataset_id} 无样本")
            return None
        training_data = []
        for s in samples:
            if s.get("messages"):
                training_data.append({
                    "id": s.get("sample_id"),
                    "type": s.get("sample_type", "risk_assessment"),
                    "messages": s["messages"],
                    "source": s.get("source", "generated"),
                    "quality_score": s.get("quality_score", 0.5)
                })
            elif s.get("content"):
                item = s["content"]
                item["source"] = s.get("source", "postgis")
                training_data.append(item)
        if output_path is None:
            from datetime import datetime
            output_path = f"./training/data/postgis_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        print(f"[PostGIS] 导出 {len(training_data)} 条训练数据到 {output_path}")
        return output_path

    def save_finetune_history(self, model_name: str, model_path: str = None,
                              dataset_id: int = None, base_model: str = None,
                              lora_config: Dict = None, training_args: Dict = None,
                              training_samples_count: int = 0, status: str = "completed") -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO model_finetune_history (model_name, model_path, dataset_id, base_model, lora_config, training_args, training_samples_count, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (model_name, model_path, dataset_id, base_model,
                      Json(lora_config) if lora_config else None,
                      Json(training_args) if training_args else None,
                      training_samples_count, status))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"[PostGIS] 保存微调历史失败: {e}")
            return None

    def get_finetune_history(self, model_name: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                if model_name:
                    cur.execute("SELECT * FROM model_finetune_history WHERE model_name = %s ORDER BY created_at DESC LIMIT %s;", (model_name, limit))
                else:
                    cur.execute("SELECT * FROM model_finetune_history ORDER BY created_at DESC LIMIT %s;", (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[PostGIS] 获取微调历史失败: {e}")
            return []

    def list_training_datasets(self, dataset_type: str = None) -> List[Dict[str, Any]]:
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                if dataset_type:
                    cur.execute("SELECT * FROM training_datasets WHERE dataset_type = %s ORDER BY created_at DESC;", (dataset_type,))
                else:
                    cur.execute("SELECT * FROM training_datasets ORDER BY created_at DESC;")
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[PostGIS] 列出训练数据集失败: {e}")
            return []

    def close(self):
        if self.conn:
            self.conn.close()
            print("[PostGIS] 数据库连接已关闭")

_postgis_db: Optional[PostGISDatabase] = None

def get_postgis_database(**kwargs) -> PostGISDatabase:
    global _postgis_db
    if _postgis_db is None:
        _postgis_db = PostGISDatabase(**kwargs)
    return _postgis_db
