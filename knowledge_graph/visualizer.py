import sys
import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

try:
    import matplotlib.pyplot as plt
    import networkx as nx
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print('matplotlib或networkx不可用,可视化功能将受限')


@dataclass
class GraphNode:
    id: str
    name: str
    node_type: str = 'default'
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str = 'related_to'
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class KnowledgeGraphVisualizer:
    def __init__(self):
        self.node_colors = {
            'airspace_region': '#4A90D9',
            'risk_factor': '#F5A623',
            'infrastructure': '#7ED321',
            'sensitive_area': '#D0021B',
            'weather_data': '#50E3C2',
            'default': '#9B9B9B'
        }
        self.edge_colors = {
            'contains': '#4A90D9',
            'influences': '#F5A623',
            'located_in': '#7ED321',
            'related_to': '#BDBDBD',
            'default': '#9E9E9E'
        }
        self.node_sizes = {
            'airspace_region': 3500,
            'risk_factor': 2200,
            'infrastructure': 1800,
            'sensitive_area': 2000,
            'weather_data': 1500,
            'default': 2000
        }
        self.font_sizes = {
            'airspace_region': 11,
            'risk_factor': 9,
            'infrastructure': 8,
            'sensitive_area': 9,
            'weather_data': 8,
            'default': 9
        }

    def visualize_graph(self, nodes: List[GraphNode], edges: List[GraphEdge], output_path: Optional[str] = None, title: str = '知识图谱') -> Optional[str]:
        if not MATPLOTLIB_AVAILABLE:
            print('matplotlib不可用,无法生成可视化图')
            return None

        try:
            G = nx.DiGraph()

            for node in nodes:
                node_color = self.node_colors.get(node.node_type, self.node_colors['default'])
                node_size = self.node_sizes.get(node.node_type, self.node_sizes['default'])
                G.add_node(node.id, name=node.name, type=node.node_type, color=node_color, size=node_size, properties=node.properties)

            for edge in edges:
                edge_color = self.edge_colors.get(edge.edge_type, self.edge_colors['default'])
                G.add_edge(edge.source, edge.target, type=edge.edge_type, color=edge_color, properties=edge.properties)

            plt.figure(figsize=(16, 12), facecolor='#FAFAFA')
            pos = self._hierarchical_layout(G)

            node_colors_list = [G.nodes[node]['color'] for node in G.nodes]
            node_sizes_list = [G.nodes[node]['size'] for node in G.nodes]
            nx.draw_networkx_nodes(G, pos, node_color=node_colors_list, node_size=node_sizes_list, alpha=0.85, edgecolors='#FFFFFF', linewidths=2)

            edge_colors_list = [G.edges[edge]['color'] for edge in G.edges]
            nx.draw_networkx_edges(G, pos, edge_color=edge_colors_list, width=1.5, alpha=0.5, arrows=True, arrowsize=15, arrowstyle='-|>', connectionstyle='arc3,rad=0.1')

            labels = {node: G.nodes[node]['name'] for node in G.nodes}
            nx.draw_networkx_labels(G, pos, labels, font_size=9, font_weight='normal', font_family='Microsoft YaHei', font_color='#333333')

            edge_labels = {(u, v): G.edges[u, v]['type'] for u, v in G.edges}
            nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=7, font_family='Microsoft YaHei', font_color='#666666', alpha=0.7)

            plt.title(title, fontsize=14, fontweight='bold', fontfamily='Microsoft YaHei', pad=20)
            plt.axis('off')
            plt.tight_layout()

            if output_path:
                plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
                plt.close()
                print(f'知识图谱已保存到: {output_path}')
                return output_path
            else:
                plt.show()
                plt.close()
                return None

        except Exception as e:
            print(f'可视化知识图谱失败: {e}')
            import traceback
            traceback.print_exc()
            plt.close()
            return None

    def _hierarchical_layout(self, G, root=None):
        if root is None:
            for node in G.nodes():
                if G.in_degree(node) == 0:
                    root = node
                    break
            if root is None:
                root = list(G.nodes())[0]

        pos = {}
        pos[root] = (0, 0)

        from collections import deque
        queue = deque([root])
        visited = {root}
        levels = {root: 0}

        while queue:
            node = queue.popleft()
            current_level = levels[node]

            children = [n for n in G.successors(node) if n not in visited]
            for child in children:
                visited.add(child)
                levels[child] = current_level + 1
                queue.append(child)

        level_nodes = {}
        for node, level in levels.items():
            if level not in level_nodes:
                level_nodes[level] = []
            level_nodes[level].append(node)

        max_level = max(levels.values()) if levels else 0
        for level in range(max_level + 1):
            nodes_in_level = level_nodes.get(level, [])
            num_nodes = len(nodes_in_level)
            y = -level * 2

            for i, node in enumerate(nodes_in_level):
                if num_nodes == 1:
                    x = 0
                else:
                    x = (i - (num_nodes - 1) / 2) * 2.5
                pos[node] = (x, y)

        import random
        random.seed(42)
        for node in pos:
            if node != root:
                pos[node] = (pos[node][0] + random.uniform(-0.1, 0.1), pos[node][1] + random.uniform(-0.1, 0.1))

        return pos

    def visualize_from_dict(self, kg_dict: Dict[str, Any], output_path: Optional[str] = None, title: str = '知识图谱') -> Optional[str]:
        nodes = []
        edges = []

        for entity in kg_dict.get('entities', []):
            node = GraphNode(
                id=entity.get('id', ''),
                name=entity.get('name', ''),
                node_type=entity.get('type', entity.get('entity_type', 'default')),
                properties=entity.get('properties', {})
            )
            nodes.append(node)

        for relation in kg_dict.get('relations', []):
            edge = GraphEdge(
                source=relation.get('source', relation.get('source_id', '')),
                target=relation.get('target', relation.get('target_id', '')),
                edge_type=relation.get('type', relation.get('relation_type', 'related_to')),
                properties=relation.get('properties', {})
            )
            edges.append(edge)

        return self.visualize_graph(nodes, edges, output_path, title)


_visualizer_instance = None


def get_kg_visualizer() -> KnowledgeGraphVisualizer:
    global _visualizer_instance
    if _visualizer_instance is None:
        _visualizer_instance = KnowledgeGraphVisualizer()
    return _visualizer_instance


def create_general_low_altitude_kg() -> Dict[str, Any]:
    from mcp_tools.ahp_weight_calculator import get_ahp_calculator
    ahp_calc = get_ahp_calculator()
    ahp_weights = ahp_calc.get_default_weights()

    return {
        'entities': [
            {
                'id': 'low_altitude_airspace',
                'type': 'airspace_region',
                'name': '低空空域',
                'properties': {
                    'min_altitude': 0,
                    'max_altitude': 1000,
                    'description': '海拔1000米以下的空域'
                }
            },
            {
                'id': 'population_density',
                'type': 'risk_factor',
                'name': '人口密度',
                'properties': {
                    'weight': ahp_weights['人口密度'] * 100,
                    'description': '区域人口密集程度'
                }
            },
            {
                'id': 'building_density',
                'type': 'risk_factor',
                'name': '建筑物密度',
                'properties': {
                    'weight': ahp_weights['建筑物密度'] * 100,
                    'description': '建筑物分布密度和高度'
                }
            },
            {
                'id': 'air_traffic',
                'type': 'risk_factor',
                'name': '空中交通',
                'properties': {
                    'weight': ahp_weights['空中交通'] * 100,
                    'description': '航线密集度,飞行高度层'
                }
            },
            {
                'id': 'weather_condition',
                'type': 'risk_factor',
                'name': '天气条件',
                'properties': {
                    'weight': ahp_weights['天气条件'] * 100,
                    'description': '包括降水,能见度,风速等'
                }
            },
            {
                'id': 'geo_topology',
                'type': 'risk_factor',
                'name': '地理拓扑',
                'properties': {
                    'weight': ahp_weights['地理拓扑'] * 100,
                    'description': '地理拓扑因素,评估飞行航线与周边重要设施的空间邻近程度'
                }
            },
            {
                'id': 'generic_airport',
                'type': 'infrastructure',
                'name': '机场',
                'properties': {
                    'infra_type': 'airport',
                    'description': '通用航空机场'
                }
            },
            {
                'id': 'generic_train_station',
                'type': 'infrastructure',
                'name': '火车站',
                'properties': {
                    'infra_type': 'train_station',
                    'description': '铁路交通枢纽'
                }
            },
            {
                'id': 'generic_government',
                'type': 'sensitive_area',
                'name': '政府机关',
                'properties': {
                    'area_type': 'government',
                    'priority': 1
                }
            },
            {
                'id': 'generic_university',
                'type': 'sensitive_area',
                'name': '大学',
                'properties': {
                    'area_type': 'university',
                    'priority': 2
                }
            },
            {
                'id': 'generic_nature_reserve',
                'type': 'sensitive_area',
                'name': '自然保护区',
                'properties': {
                    'area_type': 'nature_reserve',
                    'priority': 1
                }
            }
        ],
        'relations': [
            {'source': 'population_density', 'target': 'low_altitude_airspace', 'type': 'influences'},
            {'source': 'building_density', 'target': 'low_altitude_airspace', 'type': 'influences'},
            {'source': 'air_traffic', 'target': 'low_altitude_airspace', 'type': 'influences'},
            {'source': 'weather_condition', 'target': 'low_altitude_airspace', 'type': 'influences'},
            {'source': 'geo_topology', 'target': 'low_altitude_airspace', 'type': 'influences'},
            {'source': 'generic_airport', 'target': 'low_altitude_airspace', 'type': 'located_in'},
            {'source': 'generic_train_station', 'target': 'low_altitude_airspace', 'type': 'located_in'},
            {'source': 'generic_government', 'target': 'low_altitude_airspace', 'type': 'located_in'},
            {'source': 'generic_university', 'target': 'low_altitude_airspace', 'type': 'located_in'},
            {'source': 'generic_nature_reserve', 'target': 'low_altitude_airspace', 'type': 'located_in'}
        ]
    }


if __name__ == '__main__':
    print('创建通用低空空域知识图谱...')
    general_kg = create_general_low_altitude_kg()
    print('节点数量:', len(general_kg['entities']))
    print('关系数量:', len(general_kg['relations']))
    print('\n尝试可视化...')

    if MATPLOTLIB_AVAILABLE:
        visualizer = get_kg_visualizer()
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'general_low_altitude_kg.png')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result_path = visualizer.visualize_from_dict(general_kg, output_path=output_path, title='通用低空空域风险评估知识图谱')
        print(f'\n可视化完成!图片保存在: {result_path}')
    else:
        print('\nmatplotlib不可用,跳过可视化')
