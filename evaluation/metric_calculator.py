import sys
import os
import math
from typing import Dict, Any, List, Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class MetricCalculator:
    @staticmethod
    def calculate_accuracy(predicted: List[str], actual: List[str]) -> float:
        if not predicted and not actual:
            return 1.0
        pred_set = set(predicted)
        actual_set = set(actual)
        intersection = pred_set & actual_set
        union = pred_set | actual_set
        if not union:
            return 0.0
        return len(intersection) / len(union)
    @staticmethod
    def calculate_completeness(predicted: List[str], actual: List[str]) -> float:
        if not actual:
            return 1.0 if not predicted else 0.0
        actual_set = set(actual)
        pred_set = set(predicted)
        return len(actual_set & pred_set) / len(actual_set)
    @staticmethod
    def calculate_precision(predicted: List[str], actual: List[str]) -> float:
        if not predicted:
            return 0.0
        pred_set = set(predicted)
        actual_set = set(actual)
        return len(pred_set & actual_set) / len(pred_set)
    @staticmethod
    def calculate_recall(predicted: List[str], actual: List[str]) -> float:
        if not actual:
            return 0.0
        pred_set = set(predicted)
        actual_set = set(actual)
        return len(pred_set & actual_set) / len(actual_set)
    @staticmethod
    def calculate_f1_score(precision: float, recall: float) -> float:
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)
    @staticmethod
    def calculate_consistency(results: List[float]) -> float:
        if len(results) < 2:
            return 1.0
        mean = sum(results) / len(results)
        variance = sum((x - mean) ** 2 for x in results) / len(results)
        std_dev = math.sqrt(variance)
        return max(0, 1 - std_dev)
    @staticmethod
    def calculate_coverage(
        predicted_entities: int,
        total_entities: int,
        predicted_relations: int,
        total_relations: int
    ) -> float:
        if total_entities == 0 and total_relations == 0:
            return 1.0
        entity_coverage = predicted_entities / total_entities if total_entities > 0 else 0
        relation_coverage = predicted_relations / total_relations if total_relations > 0 else 0
        return (entity_coverage + relation_coverage) / 2
    @staticmethod
    def calculate_interpretability(
        has_risk_paths: bool,
        has_entity_descriptions: bool,
        has_relation_explanations: bool,
        has_visualization: bool
    ) -> float:
        score = 0
        if has_risk_paths:
            score += 0.3
        if has_entity_descriptions:
            score += 0.3
        if has_relation_explanations:
            score += 0.2
        if has_visualization:
            score += 0.2
        return score
    @staticmethod
    def calculate_response_time(start_time: float, end_time: float) -> float:
        return end_time - start_time
    @staticmethod
    def calculate_expert_score(
        accuracy: float,
        completeness: float,
        interpretability: float,
        coverage: float
    ) -> float:
        weights = {
            'accuracy': 0.3,
            'completeness': 0.25,
            'interpretability': 0.25,
            'coverage': 0.2
        }
        return (
            accuracy * weights['accuracy'] +
            completeness * weights['completeness'] +
            interpretability * weights['interpretability'] +
            coverage * weights['coverage']
        )
    @staticmethod
    def calculate_all_metrics(
        predicted_factors: List[str],
        actual_factors: List[str],
        predicted_entities: int,
        total_entities: int,
        predicted_relations: int,
        total_relations: int,
        response_time: float,
        has_risk_paths: bool,
        has_entity_descriptions: bool,
        has_relation_explanations: bool,
        has_visualization: bool
    ) -> Dict[str, float]:
        accuracy = MetricCalculator.calculate_accuracy(predicted_factors, actual_factors)
        completeness = MetricCalculator.calculate_completeness(predicted_factors, actual_factors)
        precision = MetricCalculator.calculate_precision(predicted_factors, actual_factors)
        recall = MetricCalculator.calculate_recall(predicted_factors, actual_factors)
        f1 = MetricCalculator.calculate_f1_score(precision, recall)
        coverage = MetricCalculator.calculate_coverage(
            predicted_entities, total_entities, predicted_relations, total_relations
        )
        interpretability = MetricCalculator.calculate_interpretability(
            has_risk_paths, has_entity_descriptions, has_relation_explanations, has_visualization
        )
        expert_score = MetricCalculator.calculate_expert_score(
            accuracy, completeness, interpretability, coverage
        )
        return {
            'accuracy': accuracy,
            'completeness': completeness,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'coverage': coverage,
            'interpretability': interpretability,
            'response_time': response_time,
            'expert_score': expert_score
        }
    @staticmethod
    def normalize_score(value: float, min_val: float = 0, max_val: float = 1) -> float:
        if max_val == min_val:
            return 0.0
        return max(0, min(1, (value - min_val) / (max_val - min_val)))