import sys
import os
import time
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.experiment_runner import ExperimentRunner
from evaluation.comparative_experiment import AssessmentMethod
def main():
    print("=" * 70)
    print("低空风险评估方法对比实验")
    print("=" * 70)
    runner = ExperimentRunner(output_dir="./evaluation/results")
    test_regions = [
        "深圳市",
        "广州市",
        "上海市",
        "北京市",
        "成都市",
        "杭州市"
    ]
    ground_truth = {
        "深圳市": {
            "risk_factors": [
                {"name": "人口密度高", "weight": 0.15},
                {"name": "高层建筑多", "weight": 0.20},
                {"name": "机场 proximity", "weight": 0.18},
                {"name": "气象条件复杂", "weight": 0.12},
                {"name": "电磁环境复杂", "weight": 0.10}
            ],
            "infrastructure": ["宝安机场", "通信塔", "高层建筑群"],
            "sensitive_areas": ["学校", "医院", "政府机关", "军事设施"]
        },
        "广州市": {
            "risk_factors": [
                {"name": "城市规模大", "weight": 0.15},
                {"name": "珠江航道", "weight": 0.12},
                {"name": "白云机场", "weight": 0.20},
                {"name": "工业区域", "weight": 0.10}
            ],
            "infrastructure": ["白云机场", "港口", "工业区"],
            "sensitive_areas": ["学校", "医院", "商业中心"]
        },
        "上海市": {
            "risk_factors": [
                {"name": "国际大都市", "weight": 0.20},
                {"name": "浦东机场", "weight": 0.18},
                {"name": "虹桥机场", "weight": 0.15},
                {"name": "黄浦江航道", "weight": 0.10}
            ],
            "infrastructure": ["浦东机场", "虹桥机场", "金融中心"],
            "sensitive_areas": ["外滩", "陆家嘴", "学校", "医院"]
        }
    }
    runner.setup_experiment(
        regions=test_regions,
        ground_truth=ground_truth
    )
    report = runner.run_experiment(
        regions=test_regions,
        methods=[
            AssessmentMethod.OUR_SYSTEM,
            AssessmentMethod.TRADITIONAL_AHP,
            AssessmentMethod.PURE_VECTOR,
            AssessmentMethod.PURE_LLM,
            AssessmentMethod.RULE_BASED,
            AssessmentMethod.HYBRID_NO_GRAPHRAG
        ],
        save_results=True
    )
    print("\n" + "=" * 70)
    print("方法排名")
    print("=" * 70)
    for i, item in enumerate(report['method_ranking'], 1):
        print(f"{i}. {item['method']}: {item['average_score']}分")
    print("\n" + "=" * 70)
    print("各指标平均值")
    print("=" * 70)
    for metric, values in report['metric_comparison'].items():
        print(f"\n{metric}:")
        for method, score in values.items():
            print(f"  {method}: {score}")
    summary_table = runner.get_method_comparison_table(report)
    print("\n" + "=" * 70)
    print("方法对比表格")
    print("=" * 70)
    print(summary_table)
    print("\n" + "=" * 70)
    print("实验完成!")
    print(f"结果保存至: ./evaluation/results/")
    print("=" * 70)
if __name__ == "__main__":
    main()