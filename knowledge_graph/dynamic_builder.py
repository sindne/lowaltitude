"""
动态知识图谱构建器
根据输入城市名称，使用大模型动态构建该城市的知识图谱
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Dict, List, Any, Optional
from knowledge_graph.builder import KnowledgeGraphBuilder
from knowledge_graph.schema import KnowledgeGraph


class DynamicKnowledgeGraphBuilder:
    """动态知识图谱构建器"""
    
    def __init__(self):
        self.common_infrastructure = {
            '北京': [
                ('北京首都国际机场', 'airport', [116.6083, 40.0799]),
                ('北京大兴国际机场', 'airport', [116.4179, 39.5091]),
                ('北京站', 'train_station', [116.4278, 39.9028]),
                ('北京西站', 'train_station', [116.3221, 39.8949]),
                ('北京南站', 'train_station', [116.3783, 39.8653]),
                ('北京北站', 'train_station', [116.3505, 39.9427]),
                ('南苑机场', 'airport', [116.3962, 39.7802])
            ],
            '上海': [
                ('上海虹桥国际机场', 'airport', [121.3356, 31.1946]),
                ('上海浦东国际机场', 'airport', [121.8044, 31.1443]),
                ('上海站', 'train_station', [121.4509, 31.2497]),
                ('上海虹桥站', 'train_station', [121.3183, 31.1938]),
                ('上海南站', 'train_station', [121.4321, 31.1572]),
                ('上海西站', 'train_station', [121.3895, 31.2636])
            ],
            '广州': [
                ('广州白云国际机场', 'airport', [113.2987, 23.3925]),
                ('广州站', 'train_station', [113.2488, 23.1475]),
                ('广州南站', 'train_station', [113.2643, 23.0021]),
                ('广州东站', 'train_station', [113.3301, 23.1472]),
                ('广州北站', 'train_station', [113.2076, 23.3784])
            ],
            '深圳': [
                ('深圳宝安国际机场', 'airport', [113.8114, 22.6388]),
                ('深圳站', 'train_station', [114.1112, 22.5378]),
                ('深圳北站', 'train_station', [114.0282, 22.6087]),
                ('福田站', 'train_station', [114.0567, 22.5403]),
                ('深圳东站', 'train_station', [114.1229, 22.5978])
            ],
            '武汉': [
                ('武汉天河国际机场', 'airport', [114.2068, 30.7832]),
                ('武昌火车站', 'train_station', [114.3183, 30.5307]),
                ('武汉站', 'train_station', [114.4186, 30.6064]),
                ('汉口火车站', 'train_station', [114.2534, 30.6208]),
                ('汉阳火车站', 'train_station', [114.2270, 30.5493])
            ],
            '成都': [
                ('成都双流国际机场', 'airport', [103.9471, 30.5785]),
                ('成都天府国际机场', 'airport', [104.4419, 30.3191]),
                ('成都站', 'train_station', [104.0731, 30.6895]),
                ('成都东站', 'train_station', [104.1013, 30.6215]),
                ('成都南站', 'train_station', [104.0673, 30.6081]),
                ('成都西站', 'train_station', [103.9588, 30.6939])
            ],
            '杭州': [
                ('杭州萧山国际机场', 'airport', [120.4342, 30.2282]),
                ('杭州站', 'train_station', [120.1854, 30.2496]),
                ('杭州东站', 'train_station', [120.2192, 30.2859]),
                ('杭州南站', 'train_station', [120.2958, 30.1701]),
                ('杭州西站', 'train_station', [120.0197, 30.2871])
            ],
            '南京': [
                ('南京禄口国际机场', 'airport', [118.8639, 31.7420]),
                ('南京站', 'train_station', [118.7993, 32.0665]),
                ('南京南站', 'train_station', [118.8023, 31.9678]),
                ('南京北站', 'train_station', [118.7391, 32.1289])
            ],
            '长沙': [
                ('长沙黄花国际机场', 'airport', [113.2278, 28.1917]),
                ('长沙站', 'train_station', [112.9976, 28.1934]),
                ('长沙南站', 'train_station', [113.0638, 28.1526]),
                ('长沙西站', 'train_station', [112.8753, 28.2785])
            ],
            '天津': [
                ('天津滨海国际机场', 'airport', [117.3526, 39.1164]),
                ('天津站', 'train_station', [117.2123, 39.1361]),
                ('天津西站', 'train_station', [117.1704, 39.1578]),
                ('天津南站', 'train_station', [117.0540, 39.0561]),
                ('滨海站', 'train_station', [117.6919, 38.9981])
            ],
            '重庆': [
                ('重庆江北国际机场', 'airport', [106.6417, 29.7192]),
                ('重庆站', 'train_station', [106.5561, 29.5539]),
                ('重庆北站', 'train_station', [106.5572, 29.6110]),
                ('重庆西站', 'train_station', [106.4533, 29.5001]),
                ('重庆南站', 'train_station', [106.5418, 29.4987])
            ],
            '石家庄': [
                ('石家庄正定国际机场', 'airport', [114.6972, 38.2821]),
                ('石家庄站', 'train_station', [114.4929, 38.0096]),
                ('石家庄北站', 'train_station', [114.4838, 38.0691]),
                ('石家庄东站', 'train_station', [114.5616, 38.0429]),
                ('正定机场站', 'train_station', [114.7101, 38.2581])
            ],
            '济南': [
                ('济南遥墙国际机场', 'airport', [117.2160, 36.8572]),
                ('济南站', 'train_station', [116.9902, 36.6706]),
                ('济南西站', 'train_station', [116.8875, 36.6684]),
                ('济南东站', 'train_station', [117.1624, 36.7074]),
                ('大明湖站', 'train_station', [117.0259, 36.6761])
            ],
            '郑州': [
                ('郑州新郑国际机场', 'airport', [113.8411, 34.5197]),
                ('郑州站', 'train_station', [113.6590, 34.7467]),
                ('郑州东站', 'train_station', [113.7730, 34.7601]),
                ('郑州西站', 'train_station', [113.4917, 34.7551]),
                ('郑州北站', 'train_station', [113.6139, 34.7944])
            ],
            '西安': [
                ('西安咸阳国际机场', 'airport', [108.7509, 34.4416]),
                ('西安站', 'train_station', [108.9670, 34.2791]),
                ('西安北站', 'train_station', [108.9418, 34.3792]),
                ('西安南站', 'train_station', [108.9659, 34.0839])
            ],
            '哈尔滨': [
                ('哈尔滨太平国际机场', 'airport', [126.2628, 45.6218]),
                ('哈尔滨站', 'train_station', [126.6421, 45.7586]),
                ('哈尔滨西站', 'train_station', [126.6061, 45.7084]),
                ('哈尔滨东站', 'train_station', [126.6873, 45.7876]),
                ('哈尔滨北站', 'train_station', [126.5537, 45.8408])
            ],
            '沈阳': [
                ('沈阳桃仙国际机场', 'airport', [123.4961, 41.6365]),
                ('沈阳站', 'train_station', [123.3983, 41.7938]),
                ('沈阳北站', 'train_station', [123.4388, 41.8180]),
                ('沈阳南站', 'train_station', [123.4043, 41.6642])
            ],
            '合肥': [
                ('合肥新桥国际机场', 'airport', [117.1351, 31.9897]),
                ('合肥站', 'train_station', [117.3161, 31.8834]),
                ('合肥南站', 'train_station', [117.2859, 31.8025])
            ],
            '昆明': [
                ('昆明长水国际机场', 'airport', [102.9215, 25.0933]),
                ('昆明站', 'train_station', [102.7219, 25.0189]),
                ('昆明南站', 'train_station', [102.8671, 24.8812])
            ],
            '福州': [
                ('福州长乐国际机场', 'airport', [119.6684, 25.9382]),
                ('福州站', 'train_station', [119.3217, 26.1147]),
                ('福州南站', 'train_station', [119.3963, 26.0334])
            ],
            '贵阳': [
                ('贵阳龙洞堡国际机场', 'airport', [106.7999, 26.5427]),
                ('贵阳站', 'train_station', [106.7040, 26.5703]),
                ('贵阳北站', 'train_station', [106.6796, 26.6218])
            ]
        }
        
        self.common_sensitive_areas = {
            '北京': [
                ('北京市政府', 'government', 1),
                ('清华大学', 'university', 2),
                ('北京大学', 'university', 2),
                ('故宫博物院', 'tourist', 2),
                ('天安门广场', 'tourist', 1),
                ('中关村', 'commercial', 2),
                ('奥林匹克公园', 'tourist', 2)
            ],
            '上海': [
                ('上海市政府', 'government', 1),
                ('复旦大学', 'university', 2),
                ('上海交通大学', 'university', 2),
                ('外滩', 'tourist', 2),
                ('东方明珠', 'tourist', 2),
                ('陆家嘴金融区', 'commercial', 1),
                ('上海迪士尼乐园', 'tourist', 2)
            ],
            '广州': [
                ('广州市政府', 'government', 1),
                ('中山大学', 'university', 2),
                ('华南理工大学', 'university', 2),
                ('广州塔', 'tourist', 2),
                ('白云山', 'nature_reserve', 1),
                ('珠江新城', 'commercial', 2)
            ],
            '深圳': [
                ('深圳市政府', 'government', 1),
                ('深圳大学', 'university', 2),
                ('南方科技大学', 'university', 2),
                ('世界之窗', 'tourist', 2),
                ('华强北', 'commercial', 2),
                ('深圳湾公园', 'nature_reserve', 1)
            ],
            '武汉': [
                ('湖北省政府', 'government', 1),
                ('武汉大学', 'university', 2),
                ('华中科技大学', 'university', 2),
                ('黄鹤楼', 'tourist', 2),
                ('东湖风景区', 'nature_reserve', 1),
                ('光谷广场', 'commercial', 2)
            ],
            '成都': [
                ('四川省政府', 'government', 1),
                ('四川大学', 'university', 2),
                ('电子科技大学', 'university', 2),
                ('武侯祠', 'tourist', 2),
                ('大熊猫繁育研究基地', 'nature_reserve', 1),
                ('天府广场', 'tourist', 2),
                ('春熙路', 'commercial', 2)
            ],
            '杭州': [
                ('浙江省政府', 'government', 1),
                ('浙江大学', 'university', 2),
                ('西湖', 'nature_reserve', 1),
                ('灵隐寺', 'tourist', 2),
                ('钱江新城', 'commercial', 2)
            ],
            '南京': [
                ('江苏省政府', 'government', 1),
                ('南京大学', 'university', 2),
                ('东南大学', 'university', 2),
                ('中山陵', 'tourist', 2),
                ('明孝陵', 'tourist', 2),
                ('玄武湖', 'nature_reserve', 1)
            ],
            '长沙': [
                ('湖南省政府', 'government', 1),
                ('湖南大学', 'university', 2),
                ('中南大学', 'university', 2),
                ('湖南师范大学', 'university', 2),
                ('橘子洲', 'tourist', 2),
                ('岳麓山', 'nature_reserve', 1),
                ('湖南省博物馆', 'tourist', 2)
            ],
            '天津': [
                ('天津市政府', 'government', 1),
                ('天津大学', 'university', 2),
                ('南开大学', 'university', 2),
                ('天津之眼', 'tourist', 2),
                ('意式风情区', 'tourist', 2),
                ('滨海新区', 'commercial', 1)
            ],
            '重庆': [
                ('重庆市政府', 'government', 1),
                ('重庆大学', 'university', 2),
                ('西南大学', 'university', 2),
                ('解放碑', 'tourist', 2),
                ('洪崖洞', 'tourist', 2),
                ('缙云山', 'nature_reserve', 1)
            ],
            '石家庄': [
                ('河北省政府', 'government', 1),
                ('石家庄市政府', 'government', 1),
                ('河北师范大学', 'university', 2),
                ('河北医科大学', 'university', 2),
                ('石家庄站广场', 'commercial', 2),
                ('正定古城', 'tourist', 2),
                ('滹沱河风景区', 'nature_reserve', 1)
            ],
            '济南': [
                ('山东省政府', 'government', 1),
                ('山东大学', 'university', 2),
                ('济南大学', 'university', 2),
                ('趵突泉', 'tourist', 2),
                ('大明湖', 'nature_reserve', 1),
                ('泉城广场', 'tourist', 2)
            ],
            '郑州': [
                ('河南省政府', 'government', 1),
                ('郑州大学', 'university', 2),
                ('河南大学', 'university', 2),
                ('二七纪念塔', 'tourist', 2),
                ('郑东新区', 'commercial', 1),
                ('黄河风景区', 'nature_reserve', 1)
            ],
            '西安': [
                ('陕西省省政府', 'government', 1),
                ('西安交通大学', 'university', 2),
                ('西北工业大学', 'university', 2),
                ('兵马俑', 'tourist', 2),
                ('大雁塔', 'tourist', 2),
                ('钟楼', 'tourist', 2),
                ('曲江新区', 'commercial', 2)
            ],
            '哈尔滨': [
                ('黑龙江省省政府', 'government', 1),
                ('哈尔滨工业大学', 'university', 2),
                ('哈尔滨工程大学', 'university', 2),
                ('中央大街', 'tourist', 2),
                ('太阳岛', 'nature_reserve', 1),
                ('冰雪大世界', 'tourist', 2)
            ],
            '沈阳': [
                ('辽宁省省政府', 'government', 1),
                ('东北大学', 'university', 2),
                ('辽宁大学', 'university', 2),
                ('沈阳故宫', 'tourist', 2),
                ('北陵公园', 'nature_reserve', 1),
                ('中街', 'commercial', 2)
            ],
            '合肥': [
                ('安徽省省政府', 'government', 1),
                ('中国科学技术大学', 'university', 2),
                ('合肥工业大学', 'university', 2),
                ('包公园', 'tourist', 2),
                ('天鹅湖', 'nature_reserve', 1)
            ],
            '昆明': [
                ('云南省省政府', 'government', 1),
                ('云南大学', 'university', 2),
                ('昆明理工大学', 'university', 2),
                ('石林风景区', 'nature_reserve', 1),
                ('滇池', 'nature_reserve', 1)
            ],
            '福州': [
                ('福建省省政府', 'government', 1),
                ('福州大学', 'university', 2),
                ('福建师范大学', 'university', 2),
                ('三坊七巷', 'tourist', 2),
                ('鼓山', 'nature_reserve', 1)
            ],
            '贵阳': [
                ('贵州省省政府', 'government', 1),
                ('贵州大学', 'university', 2),
                ('贵州师范大学', 'university', 2),
                ('甲秀楼', 'tourist', 2),
                ('黔灵山公园', 'nature_reserve', 1)
            ]
        }
        
        self.common_subdistricts = {
            '北京': ['东城区', '西城区', '朝阳区', '海淀区', '丰台区', '石景山区', '通州区', '大兴区'],
            '上海': ['浦东新区', '黄浦区', '徐汇区', '长宁区', '静安区', '虹口区', '杨浦区'],
            '广州': ['天河区', '越秀区', '海珠区', '白云区', '番禺区', '荔湾区', '黄埔区'],
            '深圳': ['南山区', '福田区', '罗湖区', '宝安区', '龙岗区', '龙华区', '光明区'],
            '武汉': ['武昌区', '洪山区', '江汉区', '硚口区', '汉阳区', '江夏区', '东西湖区'],
            '成都': ['锦江区', '武侯区', '青羊区', '金牛区', '成华区', '高新区', '天府新区'],
            '杭州': ['西湖区', '滨江区', '上城区', '拱墅区', '余杭区', '萧山区', '钱塘区'],
            '南京': ['鼓楼区', '玄武区', '秦淮区', '建邺区', '栖霞区', '江宁区', '浦口区'],
            '长沙': ['芙蓉区', '天心区', '岳麓区', '开福区', '雨花区', '望城区'],
            '天津': ['和平区', '南开区', '河西区', '河东区', '河北区', '红桥区', '滨海新区'],
            '重庆': ['渝中区', '渝北区', '江北区', '南岸区', '沙坪坝区', '九龙坡区', '巴南区'],
            '西安': ['未央区', '碑林区', '雁塔区', '长安区', '莲湖区', '新城区', '灞桥区'],
            '郑州': ['金水区', '中原区', '二七区', '管城回族区', '惠济区', '郑东新区'],
            '济南': ['历下区', '历城区', '槐荫区', '天桥区', '市中区', '长清区'],
            '哈尔滨': ['南岗区', '道里区', '道外区', '香坊区', '松北区', '平房区'],
            '沈阳': ['和平区', '沈河区', '铁西区', '皇姑区', '大东区', '浑南区'],
            '合肥': ['蜀山区', '包河区', '庐阳区', '瑶海区', '滨湖新区'],
            '昆明': ['五华区', '盘龙区', '官渡区', '西山区', '呈贡区'],
            '福州': ['鼓楼区', '台江区', '仓山区', '晋安区', '马尾区'],
            '石家庄': ['长安区', '桥西区', '新华区', '裕华区', '栾城区'],
        }
        
        self._data_provider = None
        self._enhanced_data_fetcher = None
    
    def set_data_provider(self, provider):
        """设置数据提供者"""
        self._data_provider = provider
        print("[DynamicBuilder] 已关联数据提供者")
    
    def set_enhanced_data_fetcher(self, fetcher):
        """设置增强版数据获取器"""
        self._enhanced_data_fetcher = fetcher
        print("[DynamicBuilder] 已关联增强版数据获取器")
    
    def build_for_city(self, city_name: str, use_llm: bool = False) -> KnowledgeGraph:
        """为指定城市构建知识图谱（API优先）"""
        builder = KnowledgeGraphBuilder()
        from knowledge_graph.schema import RelationType
        
        # ========== 第一层：城市 ==========
        city_id = builder.add_airspace_region(
            name=city_name, region_type='city',
            boundary=[], min_altitude=0.0, max_altitude=1000.0,
            properties={'importance': 1.0}
        )
        
        entity_ids = {
            'city': city_id,
            'infrastructure': [],
            'sensitive_areas': [],
            'risk_factors': []
        }
        
        # ========== 第二层：敏感区域（API优先 → 内置兜底） ==========
        self._add_sensitive_areas(builder, city_name, entity_ids, city_id)
        
        if not entity_ids['sensitive_areas']:
            print(f"[DynamicBuilder] API无敏感区域数据，使用内置数据兜底")
            sensitive_from_builtin = self._get_city_sensitive_areas(city_name)
            for name, stype, priority in sensitive_from_builtin:
                importance = 1.0 if priority == 1 else 0.8 if priority == 2 else 0.6
                area_id = builder.add_sensitive_area(
                    name, stype, priority,
                    properties={'importance': importance}
                )
                entity_ids['sensitive_areas'].append(area_id)
                builder.add_relation(city_id, area_id, RelationType.CONTAINS)
        
        # ========== 第二层：基础设施（API优先 → 内置兜底） ==========
        self._add_infrastructure(builder, city_name, entity_ids, city_id)
        
        if not entity_ids['infrastructure']:
            print(f"[DynamicBuilder] API无基础设施数据，使用内置数据兜底")
            infra_from_builtin = self._get_city_infrastructure(city_name)
            for name, itype, loc in infra_from_builtin:
                importance = 0.85 if itype == 'airport' else 0.7
                infra_id = builder.add_infrastructure(
                    name, itype, loc,
                    properties={'importance': importance}
                )
                entity_ids['infrastructure'].append(infra_id)
                builder.add_relation(city_id, infra_id, RelationType.CONTAINS)
        
        # ========== 第三层：风险因素（基于城市数据，全面覆盖） ==========
        from mcp_tools.ahp_weight_calculator import get_ahp_calculator
        from mcp_tools.llm_weight_adjuster import get_llm_weight_adjuster
        
        ahp_calc = get_ahp_calculator()
        llm_adjuster = get_llm_weight_adjuster()
        base_weights = ahp_calc.get_default_weights()
        
        pop_density = 1500
        bldg_density = 0.5
        avg_wind = 5.0
        geo_score = 0.5
        elevation_val = 50
        airport_count = 1
        precip_val = 0.3
        visibility_val = 10.0
        
        if self._data_provider:
            try:
                city_info = self._data_provider.get_city_info(city_name)
                if city_info:
                    pop_density = city_info.get('population_density', 1500)
                    bldg_density = city_info.get('building_density', 0.5)
                    avg_wind = city_info.get('avg_wind_speed', 5.0)
                    geo_score = city_info.get('geo_topology_score', 0.5)
                    elevation_val = city_info.get('elevation', 50)
                    airport_count = city_info.get('num_airports', 1)
                    precip_val = city_info.get('precipitation_prob', 0.3)
                    visibility_val = city_info.get('visibility', 10.0)
                    
                    city_data_for_weights = {
                        'population_density': pop_density,
                        'building_density': bldg_density,
                        'num_airports': airport_count,
                        'avg_wind_speed': avg_wind,
                        'geo_topology_score': geo_score,
                        'has_typhoon': city_info.get('has_typhoon', False),
                        'has_sensitive_facilities': len(entity_ids['sensitive_areas']) > 0
                    }
            except Exception as e:
                city_data_for_weights = {}
                print(f"[DynamicBuilder] 获取城市数据失败: {e}")
        
        if not city_data_for_weights:
            city_data_for_weights = {
                'population_density': pop_density,
                'building_density': bldg_density,
                'num_airports': airport_count,
                'avg_wind_speed': avg_wind,
                'geo_topology_score': geo_score,
                'has_typhoon': False,
                'has_sensitive_facilities': len(entity_ids['sensitive_areas']) > 0
            }
        
        adjusted_weights = llm_adjuster.adjust_weights_by_llm(base_weights, city_data_for_weights)
        
        # 从AHP权重推导子因素权重（5大类→15个子因素）
        base_pop_w = adjusted_weights.get("人口密度", 0.416)
        base_building_w = adjusted_weights.get("建筑物密度", 0.161)
        base_air_w = adjusted_weights.get("空中交通", 0.262)
        base_weather_w = adjusted_weights.get("天气条件", 0.098)
        base_geo_w = adjusted_weights.get("地理拓扑", 0.063)
        
        pop_val = min(1.0, pop_density / 8000)
        building_val = min(1.0, bldg_density)
        air_val = min(1.0, len(entity_ids['infrastructure']) / 10)
        weather_val = min(1.0, avg_wind / 15)
        geo_val = min(1.0, geo_score)
        
        # 15个风险因素全面覆盖各类飞行安全影响因素
        num_infra = len(entity_ids['infrastructure'])
        num_sensitive = len(entity_ids['sensitive_areas'])
        is_coastal = airport_count >= 2
        
        risk_factors = [
            # 人口因素类（权重 ~41%）
            ('人口密度', 'demographic', base_pop_w * 0.35 * 100, round(pop_val, 2),
             {'real_value': f'{pop_density}人/km²'}),
            ('人口流动指数', 'population_mobility', base_pop_w * 0.25 * 100,
             round(min(1.0, (num_infra + num_sensitive) / 30), 2), {}),
            ('夜间人口聚集', 'night_population', base_pop_w * 0.20 * 100,
             round(min(1.0, pop_density / 15000), 2), {}),
            ('公共设施密度', 'public_facilities', base_pop_w * 0.20 * 100,
             round(min(1.0, num_sensitive / 15), 2), {}),
            
            # 建筑物因素类（权重 ~16%）
            ('建筑物密度', 'building_density', base_building_w * 0.40 * 100,
             round(building_val, 2), {}),
            ('建筑物平均高度', 'building_height', base_building_w * 0.35 * 100,
             round(min(1.0, bldg_density * 1.5), 2), {}),
            ('高层建筑集中度', 'highrise_concentration', base_building_w * 0.25 * 100,
             round(min(1.0, bldg_density * 1.2), 2), {}),
            
            # 空中交通因素类（权重 ~26%）
            ('空中交通量', 'air_traffic', base_air_w * 0.35 * 100,
             round(air_val, 2), {}),
            ('航线密度', 'flight_route_density', base_air_w * 0.30 * 100,
             round(min(1.0, airport_count / 5), 2), {}),
            ('机场禁飞区覆盖', 'no_fly_zone', base_air_w * 0.20 * 100,
             round(min(1.0, airport_count * 0.25), 2), {}),
            ('低空空域管控', 'airspace_control', base_air_w * 0.15 * 100,
             round(0.55 if num_infra >= 3 else 0.25, 2), {}),
            
            # 天气因素类（权重 ~10%）
            ('平均风速', 'wind_speed', base_weather_w * 0.40 * 100,
             round(weather_val, 2), {}),
            ('降水概率', 'precipitation', base_weather_w * 0.30 * 100,
             round(precip_val, 2), {}),
            ('能见度', 'visibility', base_weather_w * 0.30 * 100,
             round(min(1.0, max(0.0, 1.0 - visibility_val / 20)), 2), {}),
            
            # 地理拓扑因素类（权重 ~6%）
            ('地形复杂度', 'terrain_complexity', base_geo_w * 0.50 * 100,
             round(geo_val, 2), {}),
            ('平均海拔', 'elevation', base_geo_w * 0.30 * 100,
             round(min(1.0, elevation_val / 3000), 2), {}),
            ('水系密度', 'water_density', base_geo_w * 0.20 * 100,
             round(0.3 if is_coastal else 0.1, 2), {})
        ]
        
        total_weight = sum(rf[2] for rf in risk_factors)
        if total_weight > 0:
            risk_factors = [
                (rf[0], rf[1], rf[2] * 100 / total_weight, rf[3], rf[4])
                for rf in risk_factors
            ]
        
        print(f"[DynamicBuilder] {city_name} 权重: {adjusted_weights}, "
              f"风险值: pop={pop_val:.2f} build={building_val:.2f} air={air_val:.2f} "
              f"weather={weather_val:.2f} geo={geo_val:.2f}")
        
        for name, ftype, weight, value, extra_props in risk_factors:
            importance = (weight / 100.0) * 0.6
            props = {'importance': importance}
            props.update(extra_props)
            factor_id = builder.add_risk_factor(
                name, ftype, round(weight, 1), value,
                properties=props
            )
            entity_ids['risk_factors'].append(factor_id)
        
        # ========== 第三层B：子区域（行政区划） ==========
        entity_ids['subdistricts'] = []
        subdistrict_names = self._get_city_subdistricts(city_name)
        for sd_name in subdistrict_names:
            sd_id = builder.add_airspace_region(
                name=sd_name, region_type='subdistrict',
                boundary=[], min_altitude=0.0, max_altitude=800.0,
                properties={'importance': 0.5, 'parent_city': city_name}
            )
            entity_ids['subdistricts'].append(sd_id)
            builder.add_relation(city_id, sd_id, RelationType.CONTAINS)
        
        # ========== 第三层C：天气数据 ==========
        entity_ids['weather_data'] = []
        weather_names = [f'{city_name}当前天气']
        for i, w_name in enumerate(weather_names):
            w_id = builder.add_weather_data(
                name=w_name,
                temperature=20.0,
                wind_speed=avg_wind,
                visibility=visibility_val,
                precipitation=precip_val,
                timestamp='',
                properties={'importance': 0.5, 'avg_wind_speed': avg_wind,
                           'visibility': visibility_val, 'precipitation': precip_val}
            )
            entity_ids['weather_data'].append(w_id)
            builder.add_relation(city_id, w_id, RelationType.ASSOCIATED_WITH)
        
        print(f"[DynamicBuilder] {city_name} 子区域: {len(entity_ids['subdistricts'])}个, "
              f"天气: {len(entity_ids['weather_data'])}条")
        
        # ========== 建立关系 ==========
        for factor_id in entity_ids['risk_factors']:
            for area_id in entity_ids['sensitive_areas']:
                builder.add_relation(area_id, factor_id, RelationType.INFLUENCES)
            for infra_id in entity_ids['infrastructure']:
                builder.add_relation(infra_id, factor_id, RelationType.INFLUENCES)
            for sub_id in entity_ids['subdistricts']:
                builder.add_relation(sub_id, factor_id, RelationType.INFLUENCES)
            for w_id in entity_ids['weather_data']:
                builder.add_relation(factor_id, w_id, RelationType.INFLUENCES)
            builder.add_relation(city_id, factor_id, RelationType.ASSOCIATED_WITH)
        
        # 同层实体互联
        for group, binding in [(entity_ids['sensitive_areas'], 0.5),
                                (entity_ids['infrastructure'], 0.3),
                                (entity_ids['risk_factors'], 0.2),
                                (entity_ids['subdistricts'], 0.15)]:
            if len(group) > 1:
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        builder.add_relation(
                            group[i], group[j], RelationType.ADJACENT_TO,
                            properties={'relation_strength': binding}
                        )
        
        kg = builder.build()
        kg.properties = {'api_sourced': True}
        print(f"[DynamicBuilder] {city_name} 知识图谱完成: "
              f"{len(kg.entities)}实体 {len(kg.relations)}关系 "
              f"(敏感区{len(entity_ids['sensitive_areas'])} 设施{len(entity_ids['infrastructure'])} "
              f"风险{len(entity_ids['risk_factors'])} 子区域{len(entity_ids['subdistricts'])} "
              f"天气{len(entity_ids['weather_data'])})")
        return kg
    
    def _add_infrastructure(self, builder: KnowledgeGraphBuilder, city_name: str, entity_ids: dict, city_id: str):
        """从数据获取器添加基础设施"""
        infrastructure_added = False
        
        # 尝试从增强版数据获取器获取
        if self._enhanced_data_fetcher:
            try:
                print(f"[DynamicBuilder] 从增强版数据获取器获取{city_name}的基础设施...")
                # 先保存城市数据到PostGIS
                self._enhanced_data_fetcher.fetch_and_save_city_data(city_name)
                # 然后获取基础设施
                infra_list = self._enhanced_data_fetcher.fetch_infrastructure_from_amap(city_name)
                if infra_list:
                    for infra in infra_list:
                        name = infra.get('name', '')
                        itype = infra.get('type', 'other')
                        location = infra.get('location', [0.0, 0.0])
                        if name and len(location) == 2:
                            importance = 0.85 if itype == 'airport' else 0.7
                            infra_id = builder.add_infrastructure(
                                name, itype, location,
                                properties={'importance': importance}
                            )
                            entity_ids['infrastructure'].append(infra_id)
                            
                            # 添加关系
                            from knowledge_graph.schema import RelationType
                            builder.add_relation(city_id, infra_id, RelationType.CONTAINS)
                    infrastructure_added = True
                    print(f"[DynamicBuilder] 从增强版数据获取器添加了{len(infra_list)}个基础设施")
            except Exception as e:
                print(f"[DynamicBuilder] 从增强版数据获取器获取基础设施失败: {e}")
        
        # 尝试从数据提供者获取
        if not infrastructure_added and self._data_provider:
            try:
                print(f"[DynamicBuilder] 从数据提供者获取{city_name}的基础设施...")
                infra_list = self._data_provider.get_infrastructure(city_name)
                if infra_list:
                    for infra in infra_list:
                        name = infra.get('name', '')
                        itype = infra.get('type', 'other')
                        location = infra.get('location', [0.0, 0.0])
                        if name and len(location) == 2:
                            importance = 0.85 if itype == 'airport' else 0.7
                            infra_id = builder.add_infrastructure(
                                name, itype, location,
                                properties={'importance': importance}
                            )
                            entity_ids['infrastructure'].append(infra_id)
                            
                            # 添加关系
                            from knowledge_graph.schema import RelationType
                            builder.add_relation(city_id, infra_id, RelationType.CONTAINS)
                    infrastructure_added = True
                    print(f"[DynamicBuilder] 从数据提供者添加了{len(infra_list)}个基础设施")
            except Exception as e:
                print(f"[DynamicBuilder] 从数据提供者获取基础设施失败: {e}")
        
        # 如果还是没有获取到任何数据，添加通用默认数据
        if not infrastructure_added:
            print(f"[DynamicBuilder] 添加通用默认基础设施到{city_name}")
            default_infra = [
                (f'{city_name}火车站', 'train_station', [0.0, 0.0]),
                (f'{city_name}高铁站', 'train_station', [0.0, 0.0]),
                (f'{city_name}长途汽车站', 'bus_station', [0.0, 0.0]),
                (f'{city_name}轨道交通枢纽', 'metro_station', [0.0, 0.0]),
                (f'{city_name}高速公路入口', 'highway_entrance', [0.0, 0.0]),
            ]
            if f'{city_name}机场' not in str(default_infra):
                default_infra.insert(0, (f'{city_name}机场', 'airport', [0.0, 0.0]))
            for name, itype, loc in default_infra:
                importance = 0.85 if itype == 'airport' else 0.7
                infra_id = builder.add_infrastructure(
                    name, itype, loc,
                    properties={'importance': importance}
                )
                entity_ids['infrastructure'].append(infra_id)
                
                # 添加关系
                from knowledge_graph.schema import RelationType
                builder.add_relation(city_id, infra_id, RelationType.CONTAINS)
    
    def _add_sensitive_areas(self, builder: KnowledgeGraphBuilder, city_name: str, entity_ids: dict, city_id: str):
        """从数据获取器添加敏感区域"""
        sensitive_added = False
        
        # 尝试从增强版数据获取器获取
        if self._enhanced_data_fetcher:
            try:
                print(f"[DynamicBuilder] 从增强版数据获取器获取{city_name}的敏感区域...")
                sensitive_list = self._enhanced_data_fetcher.fetch_sensitive_areas_from_amap(city_name)
                if sensitive_list:
                    for area in sensitive_list:
                        name = area.get('name', '')
                        atype = area.get('type', 'other')
                        priority = area.get('priority', 2)
                        if name:
                            importance = 1.0 if priority == 1 else 0.8 if priority == 2 else 0.6
                            area_id = builder.add_sensitive_area(
                                name, atype, priority,
                                properties={'importance': importance}
                            )
                            entity_ids['sensitive_areas'].append(area_id)
                            
                            # 添加关系
                            from knowledge_graph.schema import RelationType
                            builder.add_relation(city_id, area_id, RelationType.CONTAINS)
                    sensitive_added = True
                    print(f"[DynamicBuilder] 从增强版数据获取器添加了{len(sensitive_list)}个敏感区域")
            except Exception as e:
                print(f"[DynamicBuilder] 从增强版数据获取器获取敏感区域失败: {e}")
        
        # 尝试从数据提供者获取
        if not sensitive_added and self._data_provider:
            try:
                print(f"[DynamicBuilder] 从数据提供者获取{city_name}的敏感区域...")
                sensitive_list = self._data_provider.get_sensitive_areas(city_name)
                if sensitive_list:
                    for area in sensitive_list:
                        name = area.get('name', '')
                        atype = area.get('type', 'other')
                        priority = area.get('priority', 2)
                        if name:
                            importance = 1.0 if priority == 1 else 0.8 if priority == 2 else 0.6
                            area_id = builder.add_sensitive_area(
                                name, atype, priority,
                                properties={'importance': importance}
                            )
                            entity_ids['sensitive_areas'].append(area_id)
                            
                            # 添加关系
                            from knowledge_graph.schema import RelationType
                            builder.add_relation(city_id, area_id, RelationType.CONTAINS)
                    sensitive_added = True
                    print(f"[DynamicBuilder] 从数据提供者添加了{len(sensitive_list)}个敏感区域")
            except Exception as e:
                print(f"[DynamicBuilder] 从数据提供者获取敏感区域失败: {e}")
        
        # 如果还是没有获取到任何数据，添加通用默认数据
        if not sensitive_added:
            print(f"[DynamicBuilder] 添加通用默认敏感区域到{city_name}")
            default_sensitive = [
                (f'{city_name}市政府', 'government', 1),
                (f'{city_name}中心商业区', 'commercial', 2),
                (f'{city_name}大学', 'university', 2),
                (f'{city_name}人民医院', 'hospital', 1),
                (f'{city_name}中心公园', 'nature_reserve', 1),
                (f'{city_name}体育中心', 'sports', 2),
            ]
            for name, stype, priority in default_sensitive:
                importance = 1.0 if priority == 1 else 0.8 if priority == 2 else 0.6
                area_id = builder.add_sensitive_area(
                    name, stype, priority,
                    properties={'importance': importance}
                )
                entity_ids['sensitive_areas'].append(area_id)
                
                # 添加关系
                from knowledge_graph.schema import RelationType
                builder.add_relation(city_id, area_id, RelationType.CONTAINS)
    
    def _get_city_infrastructure(self, city_name: str) -> List[tuple]:
        """获取城市的基础设施"""
        for city, infra_list in self.common_infrastructure.items():
            if city in city_name:
                return infra_list
        
        default_infra = [
            (f'{city_name}机场', 'airport', [0.0, 0.0]),
            (f'{city_name}火车站', 'train_station', [0.0, 0.0])
        ]
        return default_infra
    
    def _get_city_sensitive_areas(self, city_name: str) -> List[tuple]:
        """获取城市的敏感区域"""
        for city, sensitive_list in self.common_sensitive_areas.items():
            if city in city_name:
                return sensitive_list
        
        default_sensitive = [
            (f'{city_name}政府', 'government', 1),
            (f'{city_name}大学', 'university', 2)
        ]
        return default_sensitive
    
    def _get_city_subdistricts(self, city_name: str) -> list:
        """获取城市的行政区划"""
        for city, sub_list in self.common_subdistricts.items():
            if city in city_name:
                return sub_list
        return [f'{city_name}城区', f'{city_name}新区', f'{city_name}开发区']


_dynamic_builder = None


def get_dynamic_builder() -> DynamicKnowledgeGraphBuilder:
    """获取动态构建器单例"""
    global _dynamic_builder
    if _dynamic_builder is None:
        _dynamic_builder = DynamicKnowledgeGraphBuilder()
    return _dynamic_builder
