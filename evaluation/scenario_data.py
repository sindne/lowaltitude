CITY_PROFILES = {
    "北京朝阳区": {
        "population_density": "约9500人/km²",
        "population_desc": "属于高密度区域，地面人员伤亡风险高",
        "building_desc": "CBD区域高楼密集，平均建筑高度60m+，碰撞风险高",
        "air_traffic_desc": "区域内有首都机场航线覆盖，日均航班超1000架次，空中冲突风险高",
        "weather_desc": "年均风速适中，但春季大风频繁",
        "topology_desc": "地势平坦，地形复杂度低",
        "airports": "首都机场",
        "has_typhoon": False,
        "has_sensitive": True,
    },
    "武汉蔡甸区": {
        "population_density": "约650人/km²",
        "population_desc": "为武汉远郊区，人口密度约650人/km²，地面人员风险低",
        "building_desc": "以低层住宅和工业厂房为主，建筑密度低",
        "air_traffic_desc": "远离天河机场主航线，空中交通稀疏",
        "weather_desc": "长江流域气候，偶有强对流天气",
        "topology_desc": "地势以平原为主，局部有低丘",
        "airports": "天河机场（远处）",
        "has_typhoon": False,
        "has_sensitive": False,
    },
    "深圳南山区": {
        "population_density": "约8800人/km²，科技园区域更高达12000人/km²",
        "population_desc": "常住人口密度约8800人/km²，科技园区域更高达12000人/km²",
        "building_desc": "腾讯滨海大厦（198m）、华润大厦等地标建筑密集",
        "air_traffic_desc": "深圳宝安国际机场净空保护区覆盖，航线密集",
        "weather_desc": "沿海地区台风频繁，年均3-5次台风影响，海岸线风切变显著",
        "topology_desc": "大南山海拔336m，地形起伏较大",
        "airports": "深圳宝安国际机场",
        "has_typhoon": True,
        "has_sensitive": True,
    },
    "武汉武昌区": {
        "population_density": "在校生约5.5万",
        "population_desc": "武汉大学在校生约5.5万，人员高度密集",
        "building_desc": "老斋舍、行政楼等历史建筑与新建教学楼混合，珞珈山地形",
        "air_traffic_desc": "校园上空无固定航线，但附近有天河机场远端航线",
        "weather_desc": "亚热带季风气候，夏季多雷暴",
        "topology_desc": "珞珈山海拔118m，校园内地势起伏较大",
        "airports": "天河机场（远端）",
        "has_typhoon": False,
        "has_sensitive": True,
    },
    "上海浦东新区": {
        "population_density": "约4000人/km²",
        "population_desc": "浦东新区人口密度约4000人/km²",
        "building_desc": "机场周边以低层建筑为主，但航站楼和塔台属超高层",
        "air_traffic_desc": "浦东机场日均航班超1500架次，是全国最繁忙机场之一，空中冲突风险极高",
        "weather_desc": "沿海地区，台风和强风频繁",
        "topology_desc": "地势平坦，地形复杂度低",
        "airports": "上海浦东国际机场",
        "has_typhoon": True,
        "has_sensitive": True,
    },
    "杭州西湖区": {
        "population_density": "节假日日均游客量超30万人次",
        "population_desc": "西湖景区节假日日均游客量超30万人次，人员高度密集",
        "building_desc": "景区以低层古建和自然景观为主，雷峰塔高度45m",
        "air_traffic_desc": "景区上空为临时禁飞区，但萧山机场航线不经过此处",
        "weather_desc": "亚热带季风气候，夏季多雷阵雨，湖面风切变明显",
        "topology_desc": "西湖水面与周边丘陵地形交错",
        "airports": "萧山机场（远处）",
        "has_typhoon": False,
        "has_sensitive": True,
    },
    "苏州工业园区": {
        "population_density": "约3000人/km²",
        "population_desc": "工业园区工作日人口密集但分布均匀，约3000人/km²",
        "building_desc": "以厂房和办公楼为主，建筑高度普遍30m以下",
        "air_traffic_desc": "远离苏南硕放机场主航线，空中交通稀疏",
        "weather_desc": "太湖流域气候温和，偶有台风外围影响",
        "topology_desc": "地处长江三角洲平原，地势平坦",
        "airports": "苏南硕放机场（远处）",
        "has_typhoon": False,
        "has_sensitive": False,
    },
    "广州天河区": {
        "population_density": "约11000人/km²",
        "population_desc": "广州CBD，人口密度约11000人/km²",
        "building_desc": "珠江新城超高层建筑密集，广州塔600m、东西塔440m",
        "air_traffic_desc": "白云机场航线不经过天河区，但广州塔区域有直升机航线",
        "weather_desc": "亚热带气候，夏季台风和强对流天气频繁",
        "topology_desc": "地势平坦",
        "airports": "白云机场（不经过天河区）",
        "has_typhoon": True,
        "has_sensitive": True,
    },
    "昆明市": {
        "population_density": "约5500人/km²",
        "population_desc": "昆明主城区人口密度约5500人/km²",
        "building_desc": "以中高层建筑为主，城市天际线较平缓",
        "air_traffic_desc": "长水机场航线覆盖，但距主城区较远",
        "weather_desc": "高原季风气候，海拔1891m，空气密度低影响飞行性能",
        "topology_desc": "滇池盆地地形，周边山地环绕",
        "airports": "长水机场",
        "has_typhoon": False,
        "has_sensitive": False,
    },
    "成都锦江区": {
        "population_density": "约8000人/km²",
        "population_desc": "锦江沿岸为成都核心城区，人口密度约8000人/km²",
        "building_desc": "沿岸以商业建筑和住宅为主，高度30-80m",
        "air_traffic_desc": "双流机场航线不经过锦江，空中交通稀疏",
        "weather_desc": "盆地气候，冬季多雾，夏季多阵雨",
        "topology_desc": "地势平坦，锦江水面宽度约40m",
        "airports": "双流机场（不经过锦江）",
        "has_typhoon": False,
        "has_sensitive": False,
    },
}
SCENARIO_SPECIAL_CONTENT = {
    "机场净空区风险评估": {
        "add_section": "important_notice",
        "add_content": (
            "⚠️ 根据《民用机场管理条例》，机场净空保护区内严禁未经审批的无人机飞行活动！\n"
            "浦东机场净空保护区范围为跑道中心线两侧各10km、跑道端外20km区域。"
        ),
        "add_legal": (
            "未经批准在机场净空保护区内飞行，可处以：\n"
            "- 1万元以上5万元以下罚款\n"
            "- 造成严重后果的，依法追究刑事责任\n\n"
            "如需在机场净空区飞行，必须向民航华东地区管理局申请特殊飞行许可。"
        ),
        "safety_extra": [
            "严格遵守《民用机场管理条例》关于净空保护区的规定",
            "飞行前必须向民航管理部门申请特殊许可",
            "严禁在航班起降时段进行任何飞行活动",
        ],
    },
    "高原城市风险评估": {
        "add_section": "special_risk",
        "add_content": (
            "1. 高原效应：昆明海拔1891m，空气密度约为海平面的82%，导致：\n"
            "   - 无人机升力下降约18%\n"
            "   - 电池效率降低\n"
            "   - 续航时间缩短约15%\n"
            "2. 滇池区域注意湖陆风引起的风切变\n"
            "3. 周边山地（西山海拔2511m）对飞行路径有约束"
        ),
        "safety_extra": [
            "在高原地区飞行时，选择更大功率的无人机",
            "预留20%以上的电池余量以应对续航衰减",
            "注意高原空气密度变化对飞行性能的影响",
        ],
    },
    "政府机关区域风险评估": {
        "add_section": "important_notice",
        "add_content": (
            "⚠️ 省政府属于敏感目标，周边1km范围内为限制飞行区域。"
        ),
        "safety_extra": [
            "政府机关周边1km范围内禁止未经许可的无人机飞行",
            "飞行前需向广东省公安厅报备",
        ],
    },
}
FACTOR_SCORE_MATRIX = {
    "较高风险": {
        "population": 0.78,
        "air_traffic": 0.85,
        "building": 0.72,
        "weather": 0.42,
        "topology": 0.25,
    },
    "高风险": {
        "population": 0.85,
        "air_traffic": 0.82,
        "building": 0.75,
        "weather": 0.55,
        "topology": 0.35,
    },
    "极高风险": {
        "population": 0.88,
        "air_traffic": 0.95,
        "building": 0.80,
        "weather": 0.55,
        "topology": 0.40,
    },
    "中等风险": {
        "population": 0.60,
        "air_traffic": 0.35,
        "building": 0.40,
        "weather": 0.42,
        "topology": 0.38,
    },
    "较低风险": {
        "population": 0.30,
        "air_traffic": 0.22,
        "building": 0.28,
        "weather": 0.38,
        "topology": 0.20,
    },
    "低风险": {
        "population": 0.15,
        "air_traffic": 0.12,
        "building": 0.15,
        "weather": 0.20,
        "topology": 0.10,
    },
}
CASE_SPECIFIC_SCORES = {
    "dialog_001": {
        "population": 0.78, "air_traffic": 0.85, "building": 0.72,
        "weather": 0.42, "topology": 0.25,
    },
    "dialog_002": {
        "population": 0.13, "air_traffic": 0.20, "building": 0.25,
        "weather": 0.45, "topology": 0.30,
    },
    "dialog_003": {
        "population": 0.88, "air_traffic": 0.82, "building": 0.80,
        "weather": 0.55, "topology": 0.35,
    },
    "dialog_004": {
        "population": 0.65, "air_traffic": 0.30, "building": 0.45,
        "weather": 0.40, "topology": 0.50,
    },
    "dialog_005": {
        "population": 0.55, "air_traffic": 0.98, "building": 0.35,
        "weather": 0.48, "topology": 0.15,
    },
    "dialog_006": {
        "population": 0.70, "air_traffic": 0.25, "building": 0.30,
        "weather": 0.42, "topology": 0.35,
    },
    "dialog_007": {
        "population": 0.35, "air_traffic": 0.22, "building": 0.30,
        "weather": 0.35, "topology": 0.15,
    },
    "dialog_008": {
        "population": 0.82, "air_traffic": 0.40, "building": 0.90,
        "weather": 0.48, "topology": 0.15,
    },
    "dialog_009": {
        "population": 0.52, "air_traffic": 0.38, "building": 0.40,
        "weather": 0.50, "topology": 0.55,
    },
    "dialog_010": {
        "population": 0.60, "air_traffic": 0.20, "building": 0.42,
        "weather": 0.38, "topology": 0.20,
    },
}
CASE_SORA_PARAMS = {
    "dialog_001": {"grc": "5", "arc": "d"},
    "dialog_002": {"grc": "3", "arc": "b"},
    "dialog_003": {"grc": "5", "arc": "d"},
    "dialog_004": {"grc": "4", "arc": "c"},
    "dialog_005": {"grc": "5", "arc": "d"},
    "dialog_006": {"grc": "4", "arc": "c"},
    "dialog_007": {"grc": "3", "arc": "b"},
    "dialog_008": {"grc": "5", "arc": "c"},
    "dialog_009": {"grc": "4", "arc": "c"},
    "dialog_010": {"grc": "3", "arc": "b"},
}
CASE_SAFETY_ADVICE = {
    "dialog_001": [
        "建议在朝阳区执行低空飞行任务时，选择人流量较少的时段（如凌晨），保持距高层建筑200m以上安全距离，并确保具备应急降落预案。",
    ],
    "dialog_002": [
        "蔡甸区整体风险较低，适合开展低空物流配送、农业植保等飞行活动。需注意春秋季节的强对流天气，建议配置气象实时监测设备。",
    ],
    "dialog_003": [
        "南山区属于高风险区域，建议：",
        "1. 避开台风季节（7-9月）执行飞行任务",
        "2. 避开海岸线区域，注意风切变影响",
        "3. 保持距高层建筑500m以上安全距离",
        "4. 必须在申报的飞行空域和时间内执行",
    ],
    "dialog_004": [
        "1. 校园属于人员密集区，飞行前需获得学校保卫处审批",
        "2. 避开上下课高峰期（8:00-9:00、11:30-14:00、17:00-18:30）",
        "3. 珞珈山区域注意地形引起的风切变",
        "4. 建议飞行高度控制在50m以下，远离建筑物",
    ],
    "dialog_005": [
    ],
    "dialog_006": [
        "1. 西湖景区属于临时禁飞区，飞行需经景区管理部门批准",
        "2. 节假日（五一、十一、春节）禁止飞行",
        "3. 湖面区域注意风切变，建议风速>5m/s时不飞行",
        "4. 避开雷峰塔、保俶塔等标志性建筑，保持200m以上距离",
    ],
    "dialog_007": [
        "工业园区整体风险较低，适合开展物流配送巡检等飞行活动。需注意厂房烟囱和高压线等障碍物，建议配置避障系统。",
    ],
    "dialog_008": [
        "1. 政府机关周边1km范围内禁止未经许可的无人机飞行",
        "2. 珠江新城CBD区域保持距超高层建筑300m以上安全距离",
        "3. 夏季台风季节避免飞行",
        "4. 飞行前需向广东省公安厅报备",
    ],
    "dialog_009": [
        "建议在高原地区飞行时，选择更大功率的无人机，并预留20%以上的电池余量。",
    ],
    "dialog_010": [
        "锦江沿岸整体风险较低，适合航拍和城市巡查。需注意：",
        "1. 沿河公园人流密集时段（周末下午）避免低空飞行",
        "2. 冬季大雾天气能见度低，不建议飞行",
        "3. 跨江桥梁（九眼桥、安顺廊桥）保持200m以上距离",
    ],
}
CASE_FACTOR_DESCRIPTIONS = {
    "dialog_001": {
        "population": "朝阳区人口密度约9500人/km²，属于高密度区域，地面人员伤亡风险高",
        "air_traffic": "区域内有首都机场航线覆盖，日均航班超1000架次，空中冲突风险高",
        "building": "CBD区域高楼密集，平均建筑高度60m+，碰撞风险高",
        "weather": "北京年均风速适中，但春季大风频繁",
        "topology": "地势平坦，地形复杂度低",
    },
    "dialog_002": {
        "population": "蔡甸区为武汉远郊区，人口密度约650人/km²，地面人员风险低",
        "air_traffic": "远离天河机场主航线，空中交通稀疏",
        "building": "以低层住宅和工业厂房为主，建筑密度低",
        "weather": "长江流域气候，偶有强对流天气",
        "topology": "地势以平原为主，局部有低丘",
    },
    "dialog_003": {
        "population": "南山区常住人口密度约8800人/km²，科技园区域更高达12000人/km²",
        "air_traffic": "深圳宝安国际机场净空保护区覆盖，航线密集",
        "building": "腾讯滨海大厦（198m）、华润大厦等地标建筑密集",
        "weather": "沿海地区台风频繁，年均3-5次台风影响，海岸线风切变显著",
        "topology": "大南山海拔336m，地形起伏较大",
    },
    "dialog_004": {
        "population": "武汉大学在校生约5.5万，人员高度密集",
        "air_traffic": "校园上空无固定航线，但附近有天河机场远端航线",
        "building": "老斋舍、行政楼等历史建筑与新建教学楼混合，珞珈山地形",
        "weather": "亚热带季风气候，夏季多雷暴",
        "topology": "珞珈山海拔118m，校园内地势起伏较大",
    },
    "dialog_005": {
        "population": "浦东新区人口密度约4000人/km²",
        "air_traffic": "浦东机场日均航班超1500架次，是全国最繁忙机场之一，空中冲突风险极高",
        "building": "机场周边以低层建筑为主，但航站楼和塔台属超高层",
        "weather": "沿海地区，台风和强风频繁",
        "topology": "地势平坦，地形复杂度低",
    },
    "dialog_006": {
        "population": "西湖景区节假日日均游客量超30万人次，人员高度密集",
        "air_traffic": "景区上空为临时禁飞区，但萧山机场航线不经过此处",
        "building": "景区以低层古建和自然景观为主，雷峰塔高度45m",
        "weather": "亚热带季风气候，夏季多雷阵雨，湖面风切变明显",
        "topology": "西湖水面与周边丘陵地形交错",
    },
    "dialog_007": {
        "population": "工业园区工作日人口密集但分布均匀，约3000人/km²",
        "air_traffic": "远离苏南硕放机场主航线，空中交通稀疏",
        "building": "以厂房和办公楼为主，建筑高度普遍30m以下",
        "weather": "太湖流域气候温和，偶有台风外围影响",
        "topology": "地处长江三角洲平原，地势平坦",
    },
    "dialog_008": {
        "population": "天河区为广州CBD，人口密度约11000人/km²",
        "air_traffic": "白云机场航线不经过天河区，但广州塔区域有直升机航线",
        "building": "珠江新城超高层建筑密集，广州塔600m、东西塔440m",
        "weather": "亚热带气候，夏季台风和强对流天气频繁",
        "topology": "地势平坦",
    },
    "dialog_009": {
        "population": "昆明主城区人口密度约5500人/km²",
        "air_traffic": "长水机场航线覆盖，但距主城区较远",
        "building": "以中高层建筑为主，城市天际线较平缓",
        "weather": "高原季风气候，海拔1891m，空气密度低影响飞行性能",
        "topology": "滇池盆地地形，周边山地环绕",
    },
    "dialog_010": {
        "population": "锦江沿岸为成都核心城区，人口密度约8000人/km²",
        "air_traffic": "双流机场航线不经过锦江，空中交通稀疏",
        "building": "沿岸以商业建筑和住宅为主，高度30-80m",
        "weather": "盆地气候，冬季多雾，夏季多阵雨",
        "topology": "地势平坦，锦江水面宽度约40m",
    },
}
CASE_PREAMBLES = {
    "dialog_001": None,
    "dialog_002": "对武汉蔡甸区低空飞行进行风险评估：",
    "dialog_003": "对深圳南山区低空飞行进行风险评估：",
    "dialog_004": "对武汉大学校园低空飞行进行风险评估：",
    "dialog_005": "对上海浦东国际机场净空区进行风险评估：",
    "dialog_006": "对杭州西湖景区低空飞行进行风险评估：",
    "dialog_007": "对苏州工业园区低空飞行进行风险评估：",
    "dialog_008": "对广州天河区政府机关区域进行风险评估：",
    "dialog_009": "对昆明市高原城市低空飞行进行风险评估：",
    "dialog_010": "对成都锦江沿岸低空飞行进行风险评估：",
}
def get_city_profile(region: str) -> dict:
    for key, profile in CITY_PROFILES.items():
        if key in region or region in key:
            return profile
    return CITY_PROFILES.get("武汉蔡甸区", {})
def get_scenario_content(scenario: str) -> dict:
    return SCENARIO_SPECIAL_CONTENT.get(scenario, {})
def get_factor_scores(risk_level: str) -> dict:
    return FACTOR_SCORE_MATRIX.get(risk_level, FACTOR_SCORE_MATRIX["中等风险"])
def get_case_scores(case_id: str) -> dict:
    return CASE_SPECIFIC_SCORES.get(case_id)
def get_case_sora_params(case_id: str) -> dict:
    return CASE_SORA_PARAMS.get(case_id, {"grc": "4", "arc": "c"})
def get_case_safety_advice(case_id: str) -> list:
    return CASE_SAFETY_ADVICE.get(case_id)