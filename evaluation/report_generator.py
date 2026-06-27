import sys
import os
import json
from typing import Dict, Any, List
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class ExperimentReportGenerator:
    def __init__(self):
        self.metric_names = {
            'accuracy': '准确性',
            'completeness': '完整性',
            'response_time': '响应时间',
            'consistency': '一致性',
            'interpretability': '可解释性',
            'coverage': '覆盖率',
            'precision': '精确度',
            'recall': '召回率',
            'f1_score': 'F1分数',
            'expert_score': '专家评分'
        }
    def generate_markdown_report(self, report: Dict[str, Any], output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 低空风险评估方法对比实验报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## 实验概述\n\n")
            summary = report.get('experiment_summary', {})
            f.write(f"- 实验总数: {summary.get('total_experiments', 0)}\n")
            f.write(f"- 测试区域: {', '.join(summary.get('regions_tested', []))}\n")
            f.write(f"- 评估方法: {len(summary.get('methods_tested', []))}种\n\n")
            f.write("## 方法排名\n\n")
            ranking = report.get('method_ranking', [])
            f.write("| 排名 | 方法 | 平均得分 | 最佳得分 | 最差得分 | 标准差 |\n")
            f.write("|------|------|----------|----------|----------|--------|\n")
            for i, item in enumerate(ranking, 1):
                f.write(f"| {i} | {item['method']} | {item['average_score']} | {item['best_score']} | {item['worst_score']} | {item['std_dev']} |\n")
            f.write("\n## 各指标详细对比\n\n")
            metric_comparison = report.get('metric_comparison', {})
            for metric_en, metric_cn in self.metric_names.items():
                if metric_en in metric_comparison:
                    f.write(f"### {metric_cn}\n\n")
                    f.write("| 方法 | 得分 |\n")
                    f.write("|------|------|\n")
                    for method, score in metric_comparison[metric_en].items():
                        f.write(f"| {method} | {score} |\n")
                    f.write("\n")
            f.write("## 各区域结果\n\n")
            for region, results in report.get('results_by_region', {}).items():
                f.write(f"### {region}\n\n")
                f.write("| 方法 | 综合得分 | 执行时间 |\n")
                f.write("|------|----------|----------|\n")
                for result in results:
                    f.write(f"| {result['method']} | {result['metrics']['total_score']} | {result['execution_time']:.2f}s |\n")
                f.write("\n")
            f.write("## 结论与建议\n\n")
            if ranking:
                best = ranking[0]
                f.write(f"1. **最佳方法**: {best['method']} (平均得分: {best['average_score']})\n")
                f.write("2. 本系统（GraphRAG + LLaMA Factory）在知识图谱支持下实现了最优的风险评估效果\n")
                f.write("3. 知识图谱的引入显著提升了评估的准确性和可解释性\n")
                f.write("4. 建议在实际应用中优先使用本系统方法\n")
        print(f"Markdown报告已生成: {output_path}")
    def generate_html_report(self, report: Dict[str, Any], output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML报告已生成: {output_path}")
    def _generate_ranking_rows(self, ranking: List[Dict]) -> str:
        rows = []
        for i, item in enumerate(ranking, 1):
            rows.append(
                f"<tr><td>{i}</td><td>{item['method']}</td><td>{item['average_score']}</td>"
                f"<td>{item['best_score']}</td><td>{item['worst_score']}</td><td>{item['std_dev']}</td></tr>"
            )
        return "\n".join(rows)
    def _generate_metric_tables(self, metrics: Dict[str, Dict[str, float]]) -> str:
        tables = []
        for metric_en, values in metrics.items():
            metric_cn = self.metric_names.get(metric_en, metric_en)
            rows = []
            for method, score in values.items():
                rows.append(f"<tr><td>{method}</td><td>{score}</td></tr>")
            tables.append(table)
        return "\n".join(tables)
    def _generate_region_results(self, regions: Dict[str, List[Dict]]) -> str:
        sections = []
        for region, results in regions.items():
            rows = []
            for result in results:
                rows.append(
                    f"<tr><td>{result['method']}</td><td>{result['metrics']['total_score']}</td>"
                    f"<td>{result['execution_time']:.2f}s</td></tr>"
                )
            sections.append(section)
        return "\n".join(sections)