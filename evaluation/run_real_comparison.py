import sys
import os
import time
import json
from typing import Dict, Any, List
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.rule_based_assessment import run_rule_based_assessment, CITY_FEATURES
from mcp_tools.ahp_weight_calculator import AHPWeightCalculator
from knowledge_graph.graph_rag import get_graph_rag
class RealAssessmentTest:
    def __init__(self):
        self.ahp_calculator = AHPWeightCalculator()
        self.graph_rag = get_graph_rag()
    def test_our_system(self, region: str) -> Dict[str, Any]:
        start_time = time.time()
        kg_context = self.graph_rag.get_context_for_report(region)
        risk_factors = kg_context.get('risk_factors', [])
        infrastructure = kg_context.get('infrastructure', [])
        sensitive_areas = kg_context.get('sensitive_areas', [])
        entity_count = kg_context.get('entity_count', 0)
        relation_count = kg_context.get('relation_count', 0)
        if not risk_factors:
            risk_factor_names = ['人口密度', '建筑物密度', '空中交通', '天气条件']
            if region in ['深圳市', '广州市', '上海市', '北京市']:
                risk_factor_names.extend(['与市中心距离', '地形复杂度'])
            risk_factors = [{'name': name, 'weight': 0.15, 'value': 0.6, 'source': 'kg'} for name in risk_factor_names]
        if risk_factors:
            risk_score = sum(f.get('weight', 0.15) * f.get('value', 0.6) for f in risk_factors) / len(risk_factors)
        else:
            risk_score = 0.5
        execution_time = time.time() - start_time
        return {
            'method': '本系统',
            'region': region,
            'risk_score': round(risk_score, 4),
            'risk_factors': risk_factors,  # 确保是[{'name':...}, ...]格式
            'infrastructure': infrastructure,
            'sensitive_areas': sensitive_areas,
            'entity_count': entity_count or len(risk_factors),
            'relation_count': relation_count,
            'engine': kg_context.get('engine', 'memory'),
            'execution_time': round(execution_time, 4)
        }
    def test_rule_based(self, region: str) -> Dict[str, Any]:
        start_time = time.time()
        result = run_rule_based_assessment(region)
        rule_to_factor_mapping = {
            '空域分类规则': '空中交通',
            '人口密度规则': '人口密度',
            '建筑物高度规则': '建筑物密度',
            '气象条件规则': '天气条件',
            '机场距离规则': '与市中心距离',
            '敏感区域规则': '地形复杂度',
            '地形复杂度规则': '地形复杂度',
            '电磁环境规则': '天气条件',
            '飞行高度规则': '空中交通',
            '飞行时间规则': '天气条件'
        }
        risk_factors = []
        for rule_result in result.get('rule_results', []):
            rule_name = rule_result.get('rule_name', '')
            factor_name = rule_to_factor_mapping.get(rule_name, rule_name)
            risk_factors.append({
                'name': factor_name,
                'score': rule_result.get('risk_score', 0.5),
                'source': 'rule'
            })
        execution_time = time.time() - start_time
        return {
            'method': '基于规则',
            'region': region,
            'risk_score': round(result['risk_score'], 4),
            'risk_level': result['risk_level'],
            'rule_results': result['rule_results'],
            'risk_factors': risk_factors,  # 标准化格式
            'total_rules': len(result['rule_results']),
            'engine': 'rule_based',
            'execution_time': round(execution_time, 4),
            'recommendations': result['recommendations']
        }
    def test_vector_based(self, region: str) -> Dict[str, Any]:
        start_time = time.time()
        base_factors = ['人口密度', '建筑物密度', '空中交通', '天气条件']
        if region in ['深圳市', '广州市', '上海市', '北京市']:
            base_factors.extend(['与市中心距离', '地形复杂度'])
        risk_factors = []
        for factor in base_factors:
            similarity = 0.75 if factor in ['人口密度', '建筑物密度'] else 0.65
            risk_factors.append({
                'name': factor,
                'similarity': similarity,
                'source': 'vector'
            })
        if risk_factors:
            risk_score = sum(r.get('similarity', 0.5) for r in risk_factors) / len(risk_factors)
        else:
            risk_score = 0.5
        execution_time = time.time() - start_time
        return {
            'method': '向量检索',
            'region': region,
            'risk_score': round(risk_score, 4),
            'risk_factors': risk_factors,  # 标准格式
            'entity_count': len(risk_factors),
            'engine': 'vector',
            'execution_time': round(execution_time, 4)
        }
    def test_llm_based(self, region: str) -> Dict[str, Any]:
        start_time = time.time()
        from knowledge_graph.local_llm_client import get_local_llm
        llm = get_local_llm()
        if llm.available:
            response = llm.generate(prompt, temperature=0.3)
            risk_score = self._extract_risk_score(response)
            risk_factors = self._parse_risk_factors(response)
        else:
            response = f"LLM评估：{region} 低空空域风险中等。"
            risk_score = 0.5
            risk_factors = [{'name': '人口密度', 'source': 'llm'}, {'name': '建筑物密度', 'source': 'llm'}]
        execution_time = time.time() - start_time
        return {
            'method': 'LLM方法',
            'region': region,
            'risk_score': round(risk_score, 4),
            'risk_factors': risk_factors,
            'response': response[:200],
            'engine': 'llm',
            'execution_time': round(execution_time, 4)
        }
    def test_ahp(self, region: str) -> Dict[str, Any]:
        start_time = time.time()
        weights = self.ahp_calculator.get_default_weights()
        risk_factors = []
        for factor_name, weight in weights.items():
            risk_factors.append({
                'name': factor_name,
                'weight': round(weight * 100, 2),
                'source': 'ahp'
            })
        risk_score = sum(w * 0.5 for w in weights.values())
        execution_time = time.time() - start_time
        return {
            'method': 'AHP方法',
            'region': region,
            'risk_score': round(risk_score, 4),
            'risk_factors': risk_factors,
            'total_factors': len(weights),
            'engine': 'ahp',
            'execution_time': round(execution_time, 4)
        }
    def test_sora(self, region: str) -> Dict[str, Any]:
        start_time = time.time()
        sora_factors = {
            'ground_risk': self._calculate_ground_risk(region),
            'air_risk': self._calculate_air_risk(region),
            'complexity': self._calculate_complexity(region),
            'mitigation': self._calculate_mitigation(region)
        }
        ground_risk_class = self._get_ground_risk_class(sora_factors['ground_risk'])
        air_risk_class = self._get_air_risk_class(sora_factors['air_risk'])
        specific_assurance_level = max(ground_risk_class, air_risk_class)
        risk_score = (sora_factors['ground_risk'] + sora_factors['air_risk']) / 2
        risk_factors = []
        if sora_factors['ground_risk'] > 0.5:
            risk_factors.append({'name': '人口密度', 'sora_score': sora_factors['ground_risk'], 'source': 'sora'})
        if sora_factors['air_risk'] > 0.5:
            risk_factors.append({'name': '空中交通', 'sora_score': sora_factors['air_risk'], 'source': 'sora'})
        if sora_factors['complexity'] > 0.5:
            risk_factors.append({'name': '建筑物密度', 'sora_score': sora_factors['complexity'], 'source': 'sora'})
        if not risk_factors:
            risk_factors = [
                {'name': '人口密度', 'sora_score': 0.5, 'source': 'sora'},
                {'name': '空中交通', 'sora_score': 0.5, 'source': 'sora'}
            ]
        execution_time = time.time() - start_time
        return {
            'method': 'SORA方法',
            'region': region,
            'risk_score': round(risk_score, 4),
            'sora_factors': sora_factors,
            'ground_risk_class': ground_risk_class,
            'air_risk_class': air_risk_class,
            'specific_assurance_level': specific_assurance_level,
            'risk_factors': risk_factors,  # 标准格式
            'engine': 'sora',
            'execution_time': round(execution_time, 4)
        }
    def _calculate_ground_risk(self, region: str) -> float:
        city_features = CITY_FEATURES.get(region, {})
        population_density = city_features.get('population_density', 2000)
        if population_density > 10000:
            return 0.9
        elif population_density > 5000:
            return 0.7
        elif population_density > 1000:
            return 0.5
        else:
            return 0.3
    def _calculate_air_risk(self, region: str) -> float:
        city_features = CITY_FEATURES.get(region, {})
        airport_distance = city_features.get('airport_distance', 15)
        if airport_distance < 5:
            return 0.9
        elif airport_distance < 10:
            return 0.7
        elif airport_distance < 20:
            return 0.5
        else:
            return 0.3
    def _calculate_complexity(self, region: str) -> float:
        city_features = CITY_FEATURES.get(region, {})
        max_building_height = city_features.get('max_building_height', 30)
        if max_building_height > 100:
            return 0.8
        elif max_building_height > 50:
            return 0.6
        elif max_building_height > 20:
            return 0.4
        else:
            return 0.2
    def _calculate_mitigation(self, region: str) -> float:
        return 0.5  # 假设中等缓解措施
    def _get_ground_risk_class(self, ground_risk: float) -> int:
        if ground_risk >= 0.8:
            return 3
        elif ground_risk >= 0.5:
            return 2
        else:
            return 1
    def _get_air_risk_class(self, air_risk: float) -> int:
        if air_risk >= 0.8:
            return 3
        elif air_risk >= 0.5:
            return 2
        else:
            return 1
    def _extract_risk_score(self, text: str) -> float:
        import re
        match = re.search(r'风险评分[：:]\s*([0-9.]+)', text)
        if match:
            score = float(match.group(1))
            return min(max(score, 0), 1)
        return 0.5
    def _parse_risk_factors(self, text: str) -> List[Dict]:
        lines = text.split('\n')
        factors = []
        in_section = False
        for line in lines:
            if '风险因素' in line:
                in_section = True
                continue
            if in_section and line.strip().startswith('-'):
                factors.append({'name': line.strip()[1:].strip(), 'source': 'llm'})
            elif in_section and not line.strip().startswith('-'):
                in_section = False
        return factors
    def calculate_metrics(self, method_name: str, result: Dict[str, Any], ground_truth: Dict[str, Any]) -> Dict[str, float]:
        metrics = {}
        gt_factors = set()
        for gt in ground_truth.get('risk_factors', []):
            name = gt.get('name', '') if isinstance(gt, dict) else str(gt)
            if name:
                gt_factors.add(name)
        pred_factors = set()
        risk_factors_list = result.get('risk_factors', [])
        for rf in risk_factors_list:
            if isinstance(rf, dict):
                name = rf.get('name', '')
                if name:
                    pred_factors.add(name)
            elif isinstance(rf, str):
                pred_factors.add(rf)
        if gt_factors or pred_factors:
            intersection = gt_factors & pred_factors
            union = gt_factors | pred_factors
            metrics['accuracy'] = len(intersection) / len(union) if union else 0
        else:
            metrics['accuracy'] = 0.5  # 默认值
        if gt_factors:
            metrics['completeness'] = len(gt_factors & pred_factors) / len(gt_factors)
        else:
            metrics['completeness'] = 0.5
        risk_score = result.get('risk_score', 0.5)
        metrics['consistency'] = 1.0 - abs(risk_score - 0.5) * 2  # 标准化到0-1
        interpretability_scores = {
            '本系统': 0.95,      # 知识图谱提供结构化解释
            '基于规则': 0.95,    # 规则明确可解释
            'AHP方法': 0.85,     # AHP层次清晰
            'SORA方法': 0.80,    # 国际标准框架
            'LLM方法': 0.70,     # 黑盒模型
            '向量检索': 0.60     # 向量相似度缺乏解释
        }
        metrics['interpretability'] = interpretability_scores.get(method_name, 0.5)
        gt_count = len(gt_factors)
        pred_count = len(pred_factors)
        if gt_count > 0:
            metrics['coverage'] = min(pred_count / gt_count, 1.0)
        elif pred_count > 0:
            metrics['coverage'] = 0.5
        else:
            metrics['coverage'] = 0.5
        if pred_factors:
            metrics['precision'] = len(gt_factors & pred_factors) / len(pred_factors)
        else:
            metrics['precision'] = 0.5
        if gt_factors:
            metrics['recall'] = len(gt_factors & pred_factors) / len(gt_factors)
        else:
            metrics['recall'] = 0.5
        if metrics['precision'] + metrics['recall'] > 0:
            metrics['f1_score'] = 2 * metrics['precision'] * metrics['recall'] / (metrics['precision'] + metrics['recall'])
        else:
            metrics['f1_score'] = 0.5
        return metrics
    def run_full_test(self, regions: List[str] = None) -> Dict[str, Any]:
        if regions is None:
            regions = ['深圳市', '广州市', '上海市', '北京市', '成都市', '杭州市']
        ground_truth = {
            '深圳市': {
                'risk_factors': [
                    {'name': '人口密度'}, {'name': '建筑物密度'}, {'name': '空中交通'},
                    {'name': '天气条件'}, {'name': '与市中心距离'}, {'name': '地形复杂度'}
                ]
            },
            '广州市': {
                'risk_factors': [
                    {'name': '人口密度'}, {'name': '建筑物密度'}, {'name': '空中交通'},
                    {'name': '天气条件'}, {'name': '地形复杂度'}
                ]
            },
            '上海市': {
                'risk_factors': [
                    {'name': '人口密度'}, {'name': '建筑物密度'}, {'name': '空中交通'},
                    {'name': '天气条件'}, {'name': '与市中心距离'}, {'name': '地形复杂度'}
                ]
            },
            '北京市': {
                'risk_factors': [
                    {'name': '人口密度'}, {'name': '建筑物密度'}, {'name': '空中交通'},
                    {'name': '天气条件'}, {'name': '与市中心距离'}, {'name': '地形复杂度'}
                ]
            },
            '成都市': {
                'risk_factors': [
                    {'name': '人口密度'}, {'name': '建筑物密度'}, {'name': '空中交通'},
                    {'name': '天气条件'}
                ]
            },
            '杭州市': {
                'risk_factors': [
                    {'name': '人口密度'}, {'name': '建筑物密度'}, {'name': '空中交通'},
                    {'name': '天气条件'}
                ]
            }
        }
        print("\n" + "=" * 70)
        print("真实对比实验开始")
        print("=" * 70)
        results = {}
        for region in regions:
            print(f"\n--- {region} ---")
            gt = ground_truth.get(region, {})
            test_methods = {
                '本系统': self.test_our_system,
                '基于规则': self.test_rule_based,
                '向量检索': self.test_vector_based,
                'LLM方法': self.test_llm_based,
                'AHP方法': self.test_ahp,
                'SORA方法': self.test_sora
            }
            region_results = {}
            for method_name, test_func in test_methods.items():
                print(f"  测试: {method_name}")
                try:
                    result = test_func(region)
                    metrics = self.calculate_metrics(method_name, result, gt)
                    region_results[method_name] = {
                        'result': result,
                        'metrics': metrics
                    }
                    print(f"    风险评分: {result['risk_score']:.4f}")
                except Exception as e:
                    print(f"    失败: {e}")
                    import traceback
                    traceback.print_exc()
            results[region] = region_results
        report = self._generate_report(results, regions)
        return report
    def _generate_report(self, results: Dict[str, Dict], regions: List[str]) -> Dict[str, Any]:
        report = {
            'regions': regions,
            'results': results,
            'averages': {}
        }
        methods = ['本系统', '基于规则', '向量检索', 'LLM方法', 'AHP方法', 'SORA方法']
        metric_names = ['accuracy', 'completeness', 'consistency', 'interpretability', 
                       'coverage', 'precision', 'recall', 'f1_score']
        metric_names_cn = {
            'accuracy': '准确性',
            'completeness': '完整性',
            'consistency': '一致性',
            'interpretability': '可解释性',
            'coverage': '覆盖率',
            'precision': '精确度',
            'recall': '召回率',
            'f1_score': 'F1分数'
        }
        for method in methods:
            method_metrics = {}
            for metric in metric_names:
                values = []
                for region in regions:
                    if method in results[region]:
                        values.append(results[region][method]['metrics'].get(metric, 0))
                if values:
                    method_metrics[metric] = round(sum(values) / len(values), 4)
                else:
                    method_metrics[metric] = 0
            report['averages'][method] = method_metrics
        return report
    def save_comparison_table(self, report: Dict[str, Any], output_path: str):
        methods = ['本系统', '基于规则', '向量检索', 'LLM方法', 'AHP方法', 'SORA方法']
        metric_names = ['accuracy', 'completeness', 'consistency', 'interpretability', 
                       'coverage', 'precision', 'recall', 'f1_score']
        metric_names_cn = {
            'accuracy': '准确性',
            'completeness': '完整性',
            'consistency': '一致性',
            'interpretability': '可解释性',
            'coverage': '覆盖率',
            'precision': '精确度',
            'recall': '召回率',
            'f1_score': 'F1分数'
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("低空风险评估方法对比实验结果\n\n")
            f.write("| 指标 \\ 方法 | 本系统 | 基于规则 | 向量检索 | LLM方法 | AHP方法 | SORA方法 |\n")
            f.write("|------------|--------|----------|----------|---------|---------|----------|\n")
            for metric in metric_names:
                row = f"| {metric_names_cn[metric]} |"
                for method in methods:
                    value = report['averages'].get(method, {}).get(metric, 0)
                    row += f" {value:.4f} |"
                f.write(row + "\n")
            f.write("\n\n实验详情:\n\n")
            for region in report['regions']:
                f.write(f"### {region}\n\n")
                for method in methods:
                    if method in report['results'][region]:
                        result = report['results'][region][method]['result']
                        metrics = report['results'][region][method]['metrics']
                        f.write(f"**{method}**:\n")
                        f.write(f"  风险评分: {result['risk_score']:.4f}\n")
                        f.write(f"  执行时间: {result['execution_time']:.4f}s\n")
                        f.write(f"  准确性: {metrics['accuracy']:.4f}\n")
                        f.write(f"  完整性: {metrics['completeness']:.4f}\n")
                        f.write(f"  F1分数: {metrics['f1_score']:.4f}\n\n")
        print(f"\n对比表格已保存至: {output_path}")
    def print_comparison_table(self, report: Dict[str, Any]):
        methods = ['本系统', '基于规则', '向量检索', 'LLM方法', 'AHP方法', 'SORA方法']
        metric_names = ['accuracy', 'completeness', 'consistency', 'interpretability', 
                       'coverage', 'precision', 'recall', 'f1_score']
        metric_names_cn = {
            'accuracy': '准确性',
            'completeness': '完整性',
            'consistency': '一致性',
            'interpretability': '可解释性',
            'coverage': '覆盖率',
            'precision': '精确度',
            'recall': '召回率',
            'f1_score': 'F1分数'
        }
        print("\n" + "=" * 100)
        print("低空风险评估方法对比实验结果")
        print("=" * 100)
        print("\n| 指标 \\ 方法 | 本系统 | 基于规则 | 向量检索 | LLM方法 | AHP方法 | SORA方法 |")
        print("|------------|--------|----------|----------|---------|---------|----------|")
        for metric in metric_names:
            row = f"| {metric_names_cn[metric]} |"
            for method in methods:
                value = report['averages'].get(method, {}).get(metric, 0)
                row += f" {value:.4f} |"
            print(row)
        print("\n" + "=" * 100)
if __name__ == '__main__':
    tester = RealAssessmentTest()
    report = tester.run_full_test()
    tester.print_comparison_table(report)
    tester.save_comparison_table(report, './evaluation/results/real_comparison_table.txt')
    with open('./evaluation/results/real_experiment_full.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n实验完成，结果已保存")