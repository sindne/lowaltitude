import json
import os
import re
import math
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
from datetime import datetime
_CASE_SET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "training", "data", "fine_tuning_dialogue_dataset.json"
)
WEIGHTS_1GRAM = (1.0, 0.0, 0.0, 0.0)
WEIGHTS_2GRAM = (0.5, 0.5, 0.0, 0.0)
WEIGHTS_3GRAM = (1.0 / 3, 1.0 / 3, 1.0 / 3, 0.0)
WEIGHTS_4GRAM = (0.25, 0.25, 0.25, 0.25)
def _tokenize_zh(text: str) -> List[str]:
    cleaned = re.sub(r'\s+', '', text)
    return list(cleaned)
def _extract_ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
def _modified_precision(
    reference_tokens: List[str],
    candidate_tokens: List[str],
    n: int
) -> Tuple[float, int, int]:
    ref_ngrams = _extract_ngrams(reference_tokens, n)
    cand_ngrams = _extract_ngrams(candidate_tokens, n)
    if not cand_ngrams:
        return 0.0, 0, 0
    ref_counts = Counter(ref_ngrams)
    cand_counts = Counter(cand_ngrams)
    clipped_count = 0
    for ngram, count in cand_counts.items():
        clipped_count += min(count, ref_counts.get(ngram, 0))
    total_count = len(cand_ngrams)
    precision = clipped_count / total_count if total_count > 0 else 0.0
    return precision, clipped_count, total_count
def _brevity_penalty(ref_len: int, cand_len: int) -> float:
    if cand_len == 0:
        return 0.0
    if cand_len >= ref_len:
        return 1.0
    return math.exp(1.0 - ref_len / cand_len)
def compute_bleu(
    reference: str,
    candidate: str,
    weights: Tuple[float, ...] = WEIGHTS_4GRAM
) -> Dict[str, Any]:
    ref_tokens = _tokenize_zh(reference)
    cand_tokens = _tokenize_zh(candidate)
    ref_len = len(ref_tokens)
    cand_len = len(cand_tokens)
    max_n = len(weights)
    precisions: Dict[int, float] = {}
    clipped_counts: Dict[int, int] = {}
    total_counts: Dict[int, int] = {}
    for n in range(1, max_n + 1):
        p, clipped, total = _modified_precision(ref_tokens, cand_tokens, n)
        precisions[n] = p
        clipped_counts[n] = clipped
        total_counts[n] = total
    bp = _brevity_penalty(ref_len, cand_len)
    log_sum = 0.0
    for n in range(1, max_n + 1):
        w = weights[n - 1]
        if w > 0:
            p = precisions[n]
            if p > 0:
                log_sum += w * math.log(p)
            else:
                log_sum += w * (-1e10)
    bleu = bp * math.exp(log_sum) if log_sum > -1e9 else 0.0
    return {
        "bleu": round(bleu, 6),
        "brevity_penalty": round(bp, 6),
        "reference_length": ref_len,
        "candidate_length": cand_len,
        "length_ratio": round(cand_len / ref_len, 4) if ref_len > 0 else 0.0,
        "precisions": {
            f"{n}-gram": {
                "precision": round(precisions[n], 6),
                "clipped_count": clipped_counts[n],
                "total_count": total_counts[n]
            }
            for n in range(1, max_n + 1)
        }
    }
def compute_bleu_corpus(
    references: List[str],
    candidates: List[str],
    weights: Tuple[float, ...] = WEIGHTS_4GRAM
) -> Dict[str, Any]:
    assert len(references) == len(candidates), "参考文本与候选文本数量不一致"
    max_n = len(weights)
    total_clipped: Dict[int, int] = {n: 0 for n in range(1, max_n + 1)}
    total_cand: Dict[int, int] = {n: 0 for n in range(1, max_n + 1)}
    total_ref_len = 0
    total_cand_len = 0
    for ref, cand in zip(references, candidates):
        ref_tokens = _tokenize_zh(ref)
        cand_tokens = _tokenize_zh(cand)
        total_ref_len += len(ref_tokens)
        total_cand_len += len(cand_tokens)
        for n in range(1, max_n + 1):
            _, clipped, total = _modified_precision(ref_tokens, cand_tokens, n)
            total_clipped[n] += clipped
            total_cand[n] += total
    precisions: Dict[int, float] = {}
    for n in range(1, max_n + 1):
        precisions[n] = total_clipped[n] / total_cand[n] if total_cand[n] > 0 else 0.0
    bp = _brevity_penalty(total_ref_len, total_cand_len)
    log_sum = 0.0
    for n in range(1, max_n + 1):
        w = weights[n - 1]
        if w > 0:
            p = precisions[n]
            if p > 0:
                log_sum += w * math.log(p)
            else:
                log_sum += w * (-1e10)
    corpus_bleu = bp * math.exp(log_sum) if log_sum > -1e9 else 0.0
    return {
        "corpus_bleu": round(corpus_bleu, 6),
        "brevity_penalty": round(bp, 6),
        "total_reference_chars": total_ref_len,
        "total_candidate_chars": total_cand_len,
        "length_ratio": round(total_cand_len / total_ref_len, 4) if total_ref_len > 0 else 0.0,
        "precisions": {
            f"{n}-gram": {
                "precision": round(precisions[n], 6),
                "clipped_count": total_clipped[n],
                "total_count": total_cand[n]
            }
            for n in range(1, max_n + 1)
        }
    }
class BLEUEvaluator:
    def __init__(self, case_set_path: str = None):
        self.case_set_path = case_set_path or _CASE_SET_PATH
        self.cases: List[Dict] = []
        self._load_cases()
    def _load_cases(self):
        if not os.path.exists(self.case_set_path):
            print(f"[BLEU评估] 案例集文件不存在: {self.case_set_path}")
            return
        with open(self.case_set_path, "r", encoding="utf-8") as f:
            self.cases = json.load(f)
        print(f"[BLEU评估] 加载了 {len(self.cases)} 个案例")
    def get_reference_reports(self) -> List[Dict]:
        reports = []
        for case in self.cases:
            assistant_msg = None
            user_msg = None
            for msg in case.get("messages", []):
                if msg["role"] == "assistant":
                    assistant_msg = msg["content"]
                elif msg["role"] == "user":
                    user_msg = msg["content"]
            reports.append({
                "id": case.get("id", ""),
                "scenario": case.get("scenario", ""),
                "risk_level": case.get("risk_level", ""),
                "sail_level": case.get("sail_level", ""),
                "user_query": user_msg,
                "reference_report": assistant_msg,
            })
        return reports
    def evaluate_with_generated_reports(
        self,
        generated_reports: List[str],
        report_infos: List[Dict] = None
    ) -> Dict[str, Any]:
        ref_reports = self.get_reference_reports()
        if len(generated_reports) != len(ref_reports):
            raise ValueError(
                f"生成报告数量({len(generated_reports)})与案例集数量({len(ref_reports)})不匹配"
            )
        references = [r["reference_report"] for r in ref_reports]
        candidates = generated_reports
        per_case_results = []
        for i, (ref_info, cand) in enumerate(zip(ref_reports, candidates)):
            result = compute_bleu(ref_info["reference_report"], cand)
            per_case_results.append({
                "case_id": ref_info["id"],
                "scenario": ref_info["scenario"],
                "risk_level": ref_info["risk_level"],
                "sail_level": ref_info["sail_level"],
                "user_query": ref_info["user_query"],
                "bleu": result["bleu"],
                "brevity_penalty": result["brevity_penalty"],
                "reference_length": result["reference_length"],
                "candidate_length": result["candidate_length"],
                "length_ratio": result["length_ratio"],
                "precisions": result["precisions"],
            })
        corpus_result = compute_bleu_corpus(references, candidates)
        individual_bleus = {
            f"BLEU-{n}": round(
                sum(
                    compute_bleu(r, c, weights=self._get_weights(n))["bleu"]
                    for r, c in zip(references, candidates)
                ) / len(references),
                6
            )
            for n in range(1, 5)
        }
        return {
            "evaluation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "num_cases": len(self.cases),
            "case_set_path": self.case_set_path,
            "corpus_level": corpus_result,
            "individual_bleu_scores": individual_bleus,
            "per_case_results": per_case_results,
        }
    def evaluate_with_system(
        self,
        report_generator_fn
    ) -> Dict[str, Any]:
        ref_reports = self.get_reference_reports()
        generated_reports = []
        for ref_info in ref_reports:
            try:
                report = report_generator_fn(
                    scenario=ref_info["scenario"],
                    risk_level=ref_info["risk_level"],
                    sail_level=ref_info["sail_level"],
                    user_query=ref_info["user_query"],
                    reference_report=ref_info["reference_report"],
                )
                generated_reports.append(report if report else "")
            except Exception as e:
                print(f"[BLEU评估] 案例 {ref_info['id']} 报告生成失败: {e}")
                generated_reports.append("")
        return self.evaluate_with_generated_reports(generated_reports)
    @staticmethod
    def _get_weights(n: int) -> Tuple[float, ...]:
        if n == 1:
            return WEIGHTS_1GRAM
        elif n == 2:
            return WEIGHTS_2GRAM
        elif n == 3:
            return WEIGHTS_3GRAM
        else:
            return WEIGHTS_4GRAM
    def generate_report_json(self, result: Dict[str, Any]) -> str:
        return json.dumps(result, ensure_ascii=False, indent=2)
    def save_report(self, result: Dict[str, Any], output_path: str = None):
        if output_path is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "training", "evaluation_results"
            )
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"bleu_evaluation_{timestamp}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, ensure_ascii=False, indent=2, fp=f)
        print(f"[BLEU评估] 报告已保存至: {output_path}")
        return output_path
def evaluate_bleu(
    references: List[str],
    candidates: List[str]
) -> Dict[str, Any]:
    evaluator = BLEUEvaluator.__new__(BLEUEvaluator)
    evaluator.cases = []
    evaluator.case_set_path = ""
    return evaluator.evaluate_with_generated_reports(
        generated_reports=candidates,
        report_infos=[
            {"id": f"case_{i:03d}", "scenario": "", "risk_level": "", "sail_level": "", "user_query": "", "reference_report": ref}
            for i, ref in enumerate(references)
        ]
    )
def evaluate_bleu_from_cases(case_set_path: str = None) -> Dict[str, Any]:
    evaluator = BLEUEvaluator(case_set_path)
    ref_reports = evaluator.get_reference_reports()
    candidates = []
    print("\n" + "=" * 70)
    print("  BLEU 评估 — 使用模板化报告生成（系统离线模式）")
    print("=" * 70)
    from main import LLMRiskAssessor
    assessor = LLMRiskAssessor()
    for i, ref_info in enumerate(ref_reports):
        case_id = ref_info["id"]
        scenario = ref_info["scenario"]
        print(f"\n[{i + 1}/{len(ref_reports)}] 处理案例: {case_id} ({scenario})")
        region_name = _extract_region_name(ref_info["user_query"])
        dummy_sora = {
            "final_risk_score": 0.55,
            "sora_assessment": {
                "sail_level": ref_info["sail_level"],
                "ground_risk_level": 4,
                "air_risk_class": "c",
                "kinetic_energy_tier": "中等",
                "drone_kinetic_energy_j": 400,
                "operation_scenario": "标准视距内飞行"
            },
            "confidence": {"overall": 0.75},
            "risk_level": ref_info["risk_level"]
        }
        dummy_weighted = {
            "weighted_assessment": {
                "weighted_score": 0.55,
                "population_risk": 0.486,
                "building_risk": 0.143,
                "air_traffic_risk": 0.215,
                "weather_risk": 0.102,
                "topology_risk": 0.054,
                "weights": {
                    "人口风险": 0.416,
                    "建筑风险": 0.161,
                    "空交风险": 0.262,
                    "天气风险": 0.098,
                    "拓扑风险": 0.063
                }
            }
        }
        dummy_env = {"overall_risk_level": "中等", "weather_risk": 0.42}
        dummy_city = {
            "population_density": 5000,
            "building_density": "中",
            "num_airports": 1,
            "avg_wind_speed_ms": 3.5,
            "has_typhoon": False,
            "has_sensitive_facilities": True,
            "area_km2": 500
        }
        try:
            assessment = assessor.assess_risk_with_llm(
                region=region_name,
                sora_result=dummy_sora,
                weighted_result=dummy_weighted,
                environmental_factors=dummy_env,
                city_real_data=dummy_city,
            )
            report = assessment.get("assessment_report", "")
            candidates.append(report)
            print(f"  报告长度: {len(report)} 字符")
            print(f"  生成方式: {assessment.get('api_provider', 'unknown')}")
        except Exception as e:
            print(f"  报告生成失败: {e}")
            candidates.append("")
    return evaluator.evaluate_with_generated_reports(candidates)
def _extract_region_name(user_query: str) -> str:
    region_map = {
        "北京朝阳": "北京朝阳区",
        "朝阳区": "北京朝阳区",
        "武汉蔡甸": "武汉蔡甸区",
        "蔡甸区": "武汉蔡甸区",
        "深圳南山": "深圳南山区",
        "南山区": "深圳南山区",
        "武汉大学": "武汉武昌区",
        "上海浦东": "上海浦东新区",
        "浦东机场": "上海浦东新区",
        "浦东": "上海浦东新区",
        "杭州西湖": "杭州西湖区",
        "西湖": "杭州西湖区",
        "苏州工业": "苏州工业园区",
        "工业园区": "苏州工业园区",
        "广州天河": "广州天河区",
        "天河区": "广州天河区",
        "昆明": "昆明市",
        "成都锦江": "成都锦江区",
        "锦江": "成都锦江区",
    }
    for key, value in region_map.items():
        if key in user_query:
            return value
    return user_query.split("的")[0] if "的" in user_query else user_query[:4]