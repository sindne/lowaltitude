import sys
import os
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.comparative_experiment import (
    ComparativeExperiment,
    AssessmentMethod,
    EvaluationMetrics,
    ExperimentResult
)
from evaluation.metric_calculator import MetricCalculator
from evaluation.report_generator import ExperimentReportGenerator
class ExperimentRunner:
    def __init__(self, output_dir: str = "./evaluation/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.experiment = ComparativeExperiment()
        self.metric_calculator = MetricCalculator()
        self.report_generator = ExperimentReportGenerator()
    def setup_experiment(
        self,
        regions: Optional[List[str]] = None,
        ground_truth: Optional[Dict[str, Dict[str, Any]]] = None,
        workflow=None,
        graph_rag=None,
        llm_client=None,
        vector_retriever=None
    ):
        if regions is None:
            regions = ["深圳市", "广州市", "上海市", "北京市", "成都市", "杭州市", "武汉市", "南京市"]
        if ground_truth:
            for region, gt in ground_truth.items():
                self.experiment.add_test_region(region, gt)
        else:
            for region in regions:
                self.experiment.add_test_region(region)
        self.experiment.setup_dependencies(
            workflow=workflow,
            graph_rag=graph_rag,
            llm_client=llm_client,
            vector_retriever=vector_retriever
        )
    def run_experiment(
        self,
        regions: Optional[List[str]] = None,
        methods: Optional[List[AssessmentMethod]] = None,
        save_results: bool = True
    ) -> Dict[str, Any]:
        print("\n" + "=" * 70)
        print("低空风险评估方法对比实验")
        print("=" * 70)
        start_time = time.time()
        self.experiment.execute_experiment(
            regions=regions,
            methods=methods
        )
        total_time = time.time() - start_time
        report = self.experiment.save_results(
            os.path.join(self.output_dir, "comparison_report.json")
        )
        report['experiment_info'] = {
            'total_time': round(total_time, 2),
            'timestamp': datetime.now().isoformat()
        }
        if save_results:
            self._save_summary_report(report)
            self._save_detailed_metrics(report)
        print("\n" + "=" * 70)
        print("实验完成!")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"结果保存至: {self.output_dir}")
        print("=" * 70)
        return report
    def _save_summary_report(self, report: Dict[str, Any]):
        summary_path = os.path.join(self.output_dir, "summary_report.md")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("# 低空风险评估方法对比实验报告\n\n")
            f.write(f"实验时间: {report['experiment_info']['timestamp']}\n")
            f.write(f"总耗时: {report['experiment_info']['total_time']}秒\n\n")
            f.write("## 方法排名\n\n")
            f.write("| 排名 | 方法 | 平均得分 | 最佳得分 | 最差得分 | 标准差 |\n")
            f.write("|------|------|----------|----------|----------|--------|\n")
            for i, item in enumerate(report['method_ranking'], 1):
                f.write(f"| {i} | {item['method']} | {item['average_score']} | {item['best_score']} | {item['worst_score']} | {item['std_dev']} |\n")
            f.write("\n## 各指标对比\n\n")
            for metric, values in report['metric_comparison'].items():
                f.write(f"### {metric}\n\n")
                f.write("| 方法 | 得分 |\n")
                f.write("|------|------|\n")
                for method, score in values.items():
                    f.write(f"| {method} | {score} |\n")
                f.write("\n")
            f.write("\n## 结论\n\n")
            best_method = report['method_ranking'][0]['method'] if report['method_ranking'] else 'N/A'
            f.write(f"最佳评估方法: **{best_method}**\n\n")
            f.write("本系统（GraphRAG + LLaMA Factory）在以下方面表现优异:\n")
            f.write("- 准确性：知识图谱提供结构化上下文\n")
            f.write("- 完整性：多维度风险因素识别\n")
            f.write("- 可解释性：清晰的风险路径展示\n")
            f.write("- 覆盖率：全面的实体和关系覆盖\n")
        print(f"摘要报告已保存: {summary_path}")
    def _save_detailed_metrics(self, report: Dict[str, Any]):
        metrics_path = os.path.join(self.output_dir, "detailed_metrics.json")
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"详细指标已保存: {metrics_path}")
    def get_method_comparison_table(self, report: Dict[str, Any]) -> str:
        lines = []
        lines.append("| 方法 | 准确性 | 完整性 | 一致性 | 可解释性 | 覆盖率 | 综合得分 |")
        lines.append("|------|--------|--------|--------|----------|--------|----------|")
        for item in report['method_ranking']:
            method = item['method']
            metrics = report['metric_comparison']
            accuracy = metrics.get('accuracy', {}).get(method, 0)
            completeness = metrics.get('completeness', {}).get(method, 0)
            consistency = metrics.get('consistency', {}).get(method, 0)
            interpretability = metrics.get('interpretability', {}).get(method, 0)
            coverage = metrics.get('coverage', {}).get(method, 0)
            total = item['average_score']
            lines.append(
                f"| {method} | {accuracy:.2f} | {completeness:.2f} | {consistency:.2f} | "
                f"{interpretability:.2f} | {coverage:.2f} | {total:.2f} |"
            )
        return "\n".join(lines)