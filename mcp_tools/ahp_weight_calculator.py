import math
import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any

RI_TABLE = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}

SAATY_SCALE_GUIDE = """
Saaty 1-9 标度法操作指引：
  1   - 两个因素同等重要
  3   - 前者比后者稍微重要
  5   - 前者比后者明显重要
  7   - 前者比后者强烈重要
  9   - 前者比后者极端重要
  2,4,6,8 - 上述相邻判断的中间值
  倒数    - 若因素i与j的重要性之比为a_ij，则因素j与i的重要性之比为1/a_ij

判断矩阵构建规则：
  - 对角线元素必须为1（自身比较）
  - a_ij × a_ji = 1（互反性）
  - 矩阵应为正互反矩阵
  - CR < 0.1 表示判断矩阵一致性可接受

示例（5因素低空空域风险评估）：
          人口密度  空中交通  建筑物密度  天气条件  地理拓扑
  人口密度    1        2        3        4        5
  空中交通   1/2       1        2        3        4
  建筑物密度 1/3      1/2       1        2        3
  天气条件   1/4      1/3      1/2       1        2
  地理拓扑   1/5      1/4      1/3      1/2       1
"""


class AHPWeightCalculator:

    def __init__(self):
        self.criteria = ["人口密度", "空中交通", "建筑物密度", "天气条件", "地理拓扑"]

        self.judgment_matrix = np.array([
            [1,    2,    3,    4,    5],
            [1/2,  1,    2,    3,    4],
            [1/3,  1/2,  1,    2,    3],
            [1/4,  1/3,  1/2,  1,    2],
            [1/5,  1/4,  1/3,  1/2,  1],
        ], dtype=float)

        self._llm_suggest_callback: Optional[Callable] = None
        self.base_weights = self._compute_weights_from_matrix(self.judgment_matrix)
        self._cr = self._compute_consistency_ratio(self.judgment_matrix)
        self._matrix_history: List[Dict] = []

    def set_llm_callback(self, callback: Callable):
        self._llm_suggest_callback = callback

    def _compute_weights_from_matrix(self, matrix: np.ndarray) -> Dict[str, float]:
        eigenvalues, eigenvectors = np.linalg.eig(matrix)
        max_eigenvalue_index = np.argmax(eigenvalues.real)
        principal_eigenvector = np.abs(eigenvectors[:, max_eigenvalue_index].real)
        weights = principal_eigenvector / principal_eigenvector.sum()
        return {criterion: round(float(w), 3)
                for criterion, w in zip(self.criteria, weights)}

    def _compute_consistency_ratio(self, matrix: np.ndarray) -> float:
        n = len(matrix)
        eigenvalues, _ = np.linalg.eig(matrix)
        lambda_max = np.max(eigenvalues.real)
        ci = (lambda_max - n) / (n - 1) if n > 1 else 0
        ri = RI_TABLE.get(n, 1.12)
        cr = ci / ri if ri > 0 else 0.0
        return round(float(cr), 4)

    @property
    def consistency_ratio(self) -> float:
        return self._cr

    @property
    def is_consistent(self) -> bool:
        return self._cr < 0.1

    def get_judgment_matrix(self) -> List[List[float]]:
        return [[round(float(v), 3) for v in row] for row in self.judgment_matrix]

    def get_matrix_with_labels(self) -> Dict[str, Any]:
        matrix = self.get_judgment_matrix()
        return {
            "criteria": self.criteria,
            "matrix": matrix,
            "cr": self._cr,
            "is_consistent": self.is_consistent,
            "weights": self.base_weights,
            "saaty_guide": SAATY_SCALE_GUIDE
        }

    def set_judgment_matrix(self, matrix: List[List[float]]) -> Dict[str, Any]:
        arr = np.array(matrix, dtype=float)
        n = len(self.criteria)

        if arr.shape != (n, n):
            return {"ok": False, "error": f"矩阵维度必须为 {n}×{n}，当前为 {arr.shape[0]}×{arr.shape[1]}"}

        for i in range(n):
            if abs(arr[i][i] - 1.0) > 1e-6:
                return {"ok": False, "error": f"对角线元素必须为1，第{i+1}行第{i+1}列为{arr[i][i]}"}

        for i in range(n):
            for j in range(i + 1, n):
                expected = 1.0 / arr[i][j] if arr[i][j] != 0 else float('inf')
                if abs(arr[j][i] - expected) > 0.01:
                    return {
                        "ok": False,
                        "error": f"互反性检查失败：a[{i+1}][{j+1}]={arr[i][j]:.3f}，"
                                 f"但 a[{j+1}][{i+1}]={arr[j][i]:.3f}，期望={expected:.3f}"
                    }

        old_weights = dict(self.base_weights)
        old_cr = self._cr

        self.judgment_matrix = arr
        self.base_weights = self._compute_weights_from_matrix(arr)
        self._cr = self._compute_consistency_ratio(arr)

        self._matrix_history.append({
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "old_cr": old_cr,
            "new_cr": self._cr,
            "old_weights": old_weights,
            "new_weights": dict(self.base_weights)
        })

        return {
            "ok": True,
            "weights": dict(self.base_weights),
            "cr": self._cr,
            "is_consistent": self.is_consistent,
            "weight_changes": {
                c: round(self.base_weights[c] - old_weights.get(c, 0), 3)
                for c in self.criteria
            },
            "history_length": len(self._matrix_history)
        }

    def set_cell(self, row: int, col: int, value: float) -> Dict[str, Any]:
        n = len(self.criteria)
        if not (0 <= row < n and 0 <= col < n):
            return {"ok": False, "error": f"行列索引超出范围(0-{n-1})"}

        if row == col and abs(value - 1.0) > 1e-6:
            return {"ok": False, "error": "对角线元素必须为1"}

        matrix = self.get_judgment_matrix()
        matrix[row][col] = value
        if row != col:
            matrix[col][row] = 1.0 / value if value != 0 else float('inf')

        return self.set_judgment_matrix(matrix)

    def suggest_matrix_adjustment(
        self,
        feedback: str,
        city_characteristics: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        suggestions = []
        current = self.get_matrix_with_labels()
        cr = current["cr"]
        weights = current["weights"]

        if cr >= 0.1:
            suggestions.append({
                "type": "consistency",
                "severity": "high",
                "title": "一致性比率超标",
                "detail": f"当前CR={cr:.4f} ≥ 0.1，判断矩阵一致性不可接受。",
                "action": "建议检查并调整矩阵中不一致的元素对，降低逻辑矛盾。"
            })

        if city_characteristics:
            pop = city_characteristics.get("population_density", 2000)
            bld = city_characteristics.get("building_density", 0.5)
            airports = city_characteristics.get("num_airports", 1)
            wind = city_characteristics.get("avg_wind_speed", 5.0)
            geo = city_characteristics.get("geo_topology_score", 0.5)

            if pop > 5000 and weights["人口密度"] < 0.35:
                suggestions.append({
                    "type": "weight",
                    "severity": "medium",
                    "title": "人口密度权重偏低",
                    "detail": f"城市人口密度({pop})较高，当前权重({weights['人口密度']:.3f})可能不足以反映人口风险。",
                    "action": "建议适当提高[人口密度]相对于其他因素的标度值。"
                })

            if airports >= 2 and weights["空中交通"] < 0.20:
                suggestions.append({
                    "type": "weight",
                    "severity": "medium",
                    "title": "空中交通权重偏低",
                    "detail": f"城市有{airports}个机场，当前空中交通权重({weights['空中交通']:.3f})偏低。",
                    "action": "建议提高[空中交通]相对于[建筑物密度]和[天气条件]的标度值。"
                })

            if wind > 8.0 and weights["天气条件"] < 0.05:
                suggestions.append({
                    "type": "weight",
                    "severity": "low",
                    "title": "天气条件权重偏低",
                    "detail": f"平均风速{wind}m/s较高，天气条件权重({weights['天气条件']:.3f})可能偏低。",
                    "action": "建议适当提高[天气条件]相对于[地理拓扑]的标度值。"
                })

        for i, ci in enumerate(self.criteria):
            for j, cj in enumerate(self.criteria):
                if i >= j:
                    continue
                val = self.judgment_matrix[i][j]
                if val > 7:
                    suggestions.append({
                        "type": "scale",
                        "severity": "low",
                        "title": f"标度值过高: {ci} vs {cj}",
                        "detail": f"a[{i+1}][{j+1}]={val:.1f} ≥ 7，接近极端重要级别。",
                        "action": "如非确实极端重要，建议降低至5-6。"
                    })

        if not suggestions:
            suggestions.append({
                "type": "info",
                "severity": "info",
                "title": "判断矩阵状态良好",
                "detail": f"CR={cr:.4f} < 0.1，一致性可接受。当前权重分配合理。",
                "action": "无需调整。"
            })

        llm_suggestions = ""
        if self._llm_suggest_callback:
            try:
                llm_suggestions = self._llm_suggest_callback(
                    current_matrix=current,
                    city_characteristics=city_characteristics,
                    feedback=feedback
                )
            except Exception as e:
                llm_suggestions = f"[LLM建议生成失败: {e}]"

        return {
            "current": current,
            "suggestions": suggestions[:5],
            "llm_suggestions": llm_suggestions,
            "total_suggestions": len(suggestions),
            "matrix_editable": True,
            "operation_guide": SAATY_SCALE_GUIDE
        }

    def reset_to_default(self) -> Dict[str, Any]:
        self.judgment_matrix = np.array([
            [1,    2,    3,    4,    5],
            [1/2,  1,    2,    3,    4],
            [1/3,  1/2,  1,    2,    3],
            [1/4,  1/3,  1/2,  1,    2],
            [1/5,  1/4,  1/3,  1/2,  1],
        ], dtype=float)
        old_weights = dict(self.base_weights)
        self.base_weights = self._compute_weights_from_matrix(self.judgment_matrix)
        self._cr = self._compute_consistency_ratio(self.judgment_matrix)
        return {
            "ok": True,
            "weights": dict(self.base_weights),
            "cr": self._cr,
            "is_consistent": self.is_consistent,
            "message": "已恢复默认判断矩阵"
        }

    def calculate_weights(
        self,
        comparison_matrix: Optional[List[List[float]]] = None,
        city_characteristics: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        if comparison_matrix is not None:
            result = self.set_judgment_matrix(comparison_matrix)
            if not result.get("ok"):
                print(f"[AHP] 自定义矩阵无效: {result.get('error')}，使用当前矩阵")
        return self.base_weights.copy()

    def get_default_weights(self) -> Dict[str, float]:
        return self.base_weights.copy()

    def adjust_weights_by_city(
        self,
        base_weights: Dict[str, float],
        city_data: Dict[str, any]
    ) -> Dict[str, float]:
        adjusted = base_weights.copy()

        pop_density = city_data.get('population_density', 2000)
        building_density = city_data.get('building_density', 0.5)
        num_airports = city_data.get('num_airports', 1)
        wind_speed = city_data.get('avg_wind_speed', 5.0)
        geo_topology = city_data.get('geo_topology_score', 0.5)

        pop_factor = min(1.1, max(0.9, pop_density / 5000.0 * 0.1 + 0.9))
        building_factor = min(1.1, max(0.9, building_density / 0.5 * 0.1 + 0.9))
        air_traffic_factor = min(1.1, max(0.9, num_airports / 2.0 * 0.1 + 0.9))
        weather_factor = min(1.1, max(0.9, wind_speed / 5.0 * 0.1 + 0.9))
        geo_factor = min(1.1, max(0.9, geo_topology / 0.5 * 0.1 + 0.9))

        adjusted['人口密度'] *= pop_factor
        adjusted['空中交通'] *= air_traffic_factor
        adjusted['建筑物密度'] *= building_factor
        adjusted['天气条件'] *= weather_factor
        adjusted['地理拓扑'] *= geo_factor

        total = sum(adjusted.values())
        for key in adjusted:
            adjusted[key] = round(adjusted[key] / total, 3)

        sorted_weights = sorted(adjusted.values(), reverse=True)
        if not (adjusted['人口密度'] > adjusted['空中交通'] > adjusted['建筑物密度']
                > adjusted['天气条件'] > adjusted['地理拓扑']):
            return self.base_weights.copy()

        return adjusted

    def get_matrix_history(self) -> List[Dict]:
        return self._matrix_history

    def export_config(self) -> Dict[str, Any]:
        return {
            "criteria": self.criteria,
            "judgment_matrix": self.get_judgment_matrix(),
            "weights": dict(self.base_weights),
            "consistency_ratio": self._cr,
            "is_consistent": self.is_consistent
        }


_ahp_calculator = None


def get_ahp_calculator() -> AHPWeightCalculator:
    global _ahp_calculator
    if _ahp_calculator is None:
        _ahp_calculator = AHPWeightCalculator()
    return _ahp_calculator