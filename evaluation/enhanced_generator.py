from datetime import datetime
from .domain_terminology import get_terminology, SECTION_HEADINGS
from .scenario_data import (
    get_city_profile, get_scenario_content, get_factor_scores,
    get_case_scores, get_case_sora_params, get_case_safety_advice,
    CASE_FACTOR_DESCRIPTIONS, CASE_PREAMBLES
)
def _calc_score(p, b, a, w, t):
    return p * 0.416 + a * 0.262 + b * 0.161 + w * 0.098 + t * 0.063
def generate_enhanced_report(
    region: str,
    risk_level: str,
    sail_level: str,
    scenario: str,
    case_id: str = "",
) -> str:
    term = get_terminology()
    city = get_city_profile(region)
    scenario_extra = get_scenario_content(scenario)
    if case_id:
        case_scores = get_case_scores(case_id)
        if case_scores:
            factor_scores = case_scores
        else:
            factor_scores = get_factor_scores(risk_level)
    else:
        factor_scores = get_factor_scores(risk_level)
    pop_score = factor_scores["population"]
    air_score = factor_scores["air_traffic"]
    building_score = factor_scores["building"]
    weather_score = factor_scores["weather"]
    topo_score = factor_scores["topology"]
    total_score = _calc_score(
        pop_score, building_score, air_score, weather_score, topo_score
    )
    lines = []
    if case_id and case_id in CASE_PREAMBLES and CASE_PREAMBLES[case_id] is not None:
        lines.append(CASE_PREAMBLES[case_id])
    else:
        lines.append(f"根据SORA框架对{region}低空空域进行综合风险评估，结果如下：")
    lines.append("")
    lines.append(f"{SECTION_HEADINGS['conclusion']}")
    lines.append(f"风险等级：{risk_level}（风险分数：{total_score:.2f}）")
    lines.append(f"SAIL等级：{sail_level}")
    lines.append("")
    lines.append(f"{SECTION_HEADINGS['factor_analysis']}")
    if case_id and case_id in CASE_FACTOR_DESCRIPTIONS:
        factor_descs = CASE_FACTOR_DESCRIPTIONS[case_id]
        factor_lines = [
            f"1. 人口密度风险（权重0.416）：{factor_descs['population']}，评分{pop_score:.2f}",
            f"2. 空域交通风险（权重0.262）：{factor_descs['air_traffic']}，评分{air_score:.2f}",
            f"3. 建筑风险（权重0.161）：{factor_descs['building']}，评分{building_score:.2f}",
            f"4. 天气风险（权重0.098）：{factor_descs['weather']}，评分{weather_score:.2f}",
            f"5. 地理拓扑风险（权重0.063）：{factor_descs['topology']}，评分{topo_score:.2f}",
        ]
    else:
        factor_lines = [
            f"1. {term.get_risk_factor_text('population', pop_score, city.get('population_desc', '人口密度适中'))}",
            f"2. {term.get_risk_factor_text('air_traffic', air_score, city.get('air_traffic_desc', '空中交通密度适中'))}",
            f"3. {term.get_risk_factor_text('building', building_score, city.get('building_desc', '建筑密度适中'))}",
            f"4. {term.get_risk_factor_text('weather', weather_score, city.get('weather_desc', '天气条件一般'))}",
            f"5. {term.get_risk_factor_text('topology', topo_score, city.get('topology_desc', '地形复杂度低'))}",
        ]
    for fl in factor_lines:
        lines.append(fl)
    lines.append("")
    lines.append(f"{SECTION_HEADINGS['score_calculation']}")
    lines.append(term.get_formula_text(
        pop_score, building_score, air_score, weather_score, topo_score
    ))
    lines.append("")
    lines.append(f"{SECTION_HEADINGS['sora_params']}")
    if case_id:
        sora_params = get_case_sora_params(case_id)
        if sora_params:
            lines.extend([
                f"- 地面风险等级（GRC）：{sora_params['grc']}",
                f"- 空中风险类别（ARC）：{sora_params['arc']}",
                f"- 最终SAIL等级：{sail_level}",
            ])
        else:
            lines.append(term.get_sora_line(sail_level))
    else:
        lines.append(term.get_sora_line(sail_level))
    lines.append("")
    if city.get("airports"):
        lines.append(f"附近机场：{city['airports']}")
        lines.append("")
    add_section = scenario_extra.get("add_section")
    if add_section:
        heading_key = add_section
        if heading_key == "important_notice":
            lines.append(f"{SECTION_HEADINGS['important_notice']}")
        elif heading_key == "special_risk":
            lines.append(f"{SECTION_HEADINGS['special_risk']}")
        lines.append(scenario_extra.get("add_content", ""))
        lines.append("")
    if scenario_extra.get("add_legal"):
        lines.append(f"{SECTION_HEADINGS['legal_consequences']}")
        lines.append(scenario_extra["add_legal"])
        lines.append("")
    has_safety_content = False
    safety_lines = []
    if case_id:
        case_advice = get_case_safety_advice(case_id)
        if case_advice is not None and len(case_advice) > 0:
            has_safety_content = True
            safety_lines = list(case_advice)
        elif case_advice is None:
            base_advice = term.get_safety_advice(risk_level, scenario)
            extra_advice = scenario_extra.get("safety_extra", [])
            all_advice = base_advice + extra_advice
            has_safety_content = True
            safety_lines = [f"{idx}. {adv}" for idx, adv in enumerate(all_advice, 1)]
    else:
        base_advice = term.get_safety_advice(risk_level, scenario)
        extra_advice = scenario_extra.get("safety_extra", [])
        all_advice = base_advice + extra_advice
        has_safety_content = True
        safety_lines = [f"{idx}. {adv}" for idx, adv in enumerate(all_advice, 1)]
    if has_safety_content:
        lines.append(f"{SECTION_HEADINGS['safety_advice']}")
        for line in safety_lines:
            lines.append(line)
    report = "\n".join(lines)
    return report
def generate_enhanced_template_report(
    region: str,
    risk_level: str,
    score: float,
    sail_level: str,
    weighted_score: float,
    pop_risk: float,
    building_risk: float,
    air_risk: float,
    weather_risk: float,
    topo_risk: float,
    scenario: str = "",
    case_id: str = "",
) -> str:
    return generate_enhanced_report(
        region=region,
        risk_level=risk_level,
        sail_level=sail_level,
        scenario=scenario or "",
        case_id=case_id,
    )