"""
数据分析与智能工具
"""
import warnings
warnings.filterwarnings("ignore")

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict

HAS_PANDAS = False
try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except Exception:
    pass

try:
    from mcp_tools.database_tools import get_database_tool
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False


class AnalyticsTool:
    """分析工具"""
    
    def __init__(self, db_tool=None):
        """
        初始化分析工具
        
        Args:
            db_tool: 数据库工具实例（可选）
        """
        self.db_tool = db_tool
        if HAS_DATABASE and db_tool is None:
            try:
                self.db_tool = get_database_tool()
            except Exception:
                pass
    
    def analyze_risk_trends(self, region: Optional[str] = None, 
                           days: int = 30) -> Dict[str, Any]:
        """
        分析风险趋势
        
        Args:
            region: 区域名称（可选）
            days: 分析天数
            
        Returns:
            风险趋势分析结果
        """
        result = {
            'region': region or 'all',
            'analysis_period_days': days,
            'timestamp': datetime.now().isoformat()
        }
        
        if not self.db_tool:
            result['error'] = '数据库工具不可用'
            return result
        
        try:
            # 获取评估历史
            history = self.db_tool.get_assessment_history(region=region, limit=1000)
            
            if not history:
                result['message'] = '没有足够的评估数据'
                return result
            
            # 过滤指定天数的数据
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_history = []
            for item in history:
                try:
                    item_date = datetime.fromisoformat(item['created_at'])
                    if item_date >= cutoff_date:
                        filtered_history.append(item)
                except (ValueError, KeyError):
                    continue
            
            if not filtered_history:
                result['message'] = f'最近{days}天没有评估数据'
                return result
            
            result['total_assessments'] = len(filtered_history)
            
            # 风险等级分布
            risk_levels = [item['risk_level'] for item in filtered_history if 'risk_level' in item]
            if risk_levels:
                level_counts = Counter(risk_levels)
                result['risk_level_distribution'] = dict(level_counts)
                
                # 计算风险等级比例
                total = len(risk_levels)
                result['risk_level_percentages'] = {
                    level: round(count / total * 100, 2)
                    for level, count in level_counts.items()
                }
            
            # 按日期统计
            date_stats = defaultdict(int)
            for item in filtered_history:
                try:
                    item_date = datetime.fromisoformat(item['created_at']).date()
                    date_key = item_date.isoformat()
                    date_stats[date_key] += 1
                except (ValueError, KeyError):
                    continue
            
            result['daily_assessments'] = dict(sorted(date_stats.items()))
            
            # 如果有pandas，进行更高级的分析
            if HAS_PANDAS and risk_levels:
                df = pd.DataFrame(filtered_history)
                
                # 风险等级数值化（用于统计分析）
                level_mapping = {
                    '低风险': 1,
                    '较低风险': 2,
                    '中等风险': 3,
                    '较高风险': 4,
                    '高风险': 5
                }
                
                if 'risk_level' in df.columns:
                    df['risk_score'] = df['risk_level'].map(level_mapping)
                    
                    valid_scores = df['risk_score'].dropna()
                    if len(valid_scores) > 0:
                        result['risk_score_stats'] = {
                            'mean': round(float(valid_scores.mean()), 2),
                            'median': float(valid_scores.median()),
                            'std': round(float(valid_scores.std()), 2),
                            'min': int(valid_scores.min()),
                            'max': int(valid_scores.max())
                        }
            
            return result
            
        except Exception as e:
            result['error'] = f'分析失败: {str(e)}'
            return result
    
    def generate_report(self, data: List[Dict[str, Any]], 
                      report_type: str = 'risk') -> Optional[str]:
        """
        生成分析报告
        
        Args:
            data: 数据列表
            report_type: 报告类型
            
        Returns:
            报告内容
        """
        if not data:
            return None
        
        report = []
        report.append("=" * 60)
        report.append(f"低空空域风险评估分析报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        report.append("")
        
        if report_type == 'risk':
            report.append("一、总体统计")
            report.append(f"  总评估次数: {len(data)}")
            
            # 风险等级统计
            risk_levels = [item.get('risk_level', '未知') for item in data]
            level_counts = Counter(risk_levels)
            
            report.append("")
            report.append("二、风险等级分布")
            for level, count in level_counts.most_common():
                percentage = round(count / len(data) * 100, 1)
                report.append(f"  {level}: {count}次 ({percentage}%)")
            
            # 区域统计
            regions = [item.get('region', '未知') for item in data]
            region_counts = Counter(regions)
            
            report.append("")
            report.append("三、评估区域分布")
            for region, count in region_counts.most_common(10):
                report.append(f"  {region}: {count}次")
            
            # 时间趋势
            report.append("")
            report.append("四、时间趋势")
            if data and 'created_at' in data[0]:
                try:
                    dates = [datetime.fromisoformat(item['created_at']).date() for item in data]
                    date_counts = Counter(dates)
                    for date in sorted(date_counts.keys())[-7:]:
                        report.append(f"  {date}: {date_counts[date]}次")
                except Exception:
                    report.append("  无法解析时间数据")
        
        elif report_type == 'model':
            report.append("一、模型性能统计")
            # 添加模型相关分析
            
        report.append("")
        report.append("=" * 60)
        report.append("报告结束")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def get_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取统计数据
        
        Args:
            data: 数据列表
            
        Returns:
            统计信息字典
        """
        stats = {
            'total_items': len(data),
            'timestamp': datetime.now().isoformat()
        }
        
        if not data:
            return stats
        
        # 基础统计
        first_item = data[0]
        stats['available_fields'] = list(first_item.keys())
        
        # 数值字段统计
        if HAS_PANDAS:
            try:
                df = pd.DataFrame(data)
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                
                if len(numeric_cols) > 0:
                    stats['numeric_stats'] = {}
                    for col in numeric_cols:
                        col_data = df[col].dropna()
                        if len(col_data) > 0:
                            stats['numeric_stats'][col] = {
                                'count': int(len(col_data)),
                                'mean': round(float(col_data.mean()), 4),
                                'std': round(float(col_data.std()), 4),
                                'min': float(col_data.min()),
                                'max': float(col_data.max()),
                                'median': float(col_data.median())
                            }
            except Exception:
                pass
        
        # 分类字段统计
        for field in first_item.keys():
            if isinstance(first_item[field], (str, bool)) or field in ['risk_level', 'region', 'model_used']:
                try:
                    values = [item.get(field) for item in data if item.get(field) is not None]
                    if values:
                        counter = Counter(values)
                        stats[f'{field}_distribution'] = dict(counter.most_common())
                except Exception:
                    continue
        
        return stats
    
    def compare_regions(self, regions: List[str], days: int = 30) -> Dict[str, Any]:
        """
        对比多个区域的风险情况
        
        Args:
            regions: 区域名称列表
            days: 分析天数
            
        Returns:
            对比分析结果
        """
        result = {
            'regions': regions,
            'analysis_days': days,
            'timestamp': datetime.now().isoformat(),
            'comparisons': {}
        }
        
        if not self.db_tool:
            result['error'] = '数据库工具不可用'
            return result
        
        for region in regions:
            region_result = self.analyze_risk_trends(region=region, days=days)
            result['comparisons'][region] = region_result
        
        return result
    
    def analyze_model_performance(self, model_name: Optional[str] = None,
                                 days: int = 30) -> Dict[str, Any]:
        """
        分析模型性能
        
        Args:
            model_name: 模型名称（可选）
            days: 分析天数
            
        Returns:
            模型性能分析结果
        """
        result = {
            'model_name': model_name or 'all',
            'analysis_days': days,
            'timestamp': datetime.now().isoformat()
        }
        
        if not self.db_tool:
            result['error'] = '数据库工具不可用'
            return result
        
        try:
            # 获取模型信息
            models = self.db_tool.get_models(limit=100)
            
            if models:
                result['total_models'] = len(models)
                
                if model_name:
                    # 分析特定模型
                    specific_models = [m for m in models if m['model_name'] == model_name]
                    if specific_models:
                        model_info = specific_models[0]
                        result['model_info'] = {
                            'model_name': model_info['model_name'],
                            'accuracy': model_info.get('accuracy'),
                            'training_samples': model_info.get('training_samples'),
                            'created_at': model_info.get('created_at'),
                            'description': model_info.get('description')
                        }
                else:
                    # 分析所有模型
                    if HAS_PANDAS:
                        df = pd.DataFrame(models)
                        if 'accuracy' in df.columns:
                            valid_acc = df['accuracy'].dropna()
                            if len(valid_acc) > 0:
                                result['model_accuracy_stats'] = {
                                    'mean': round(float(valid_acc.mean()), 4),
                                    'best': round(float(valid_acc.max()), 4),
                                    'worst': round(float(valid_acc.min()), 4)
                                }
            
            return result
            
        except Exception as e:
            result['error'] = f'模型性能分析失败: {str(e)}'
            return result
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """
        获取整体统计信息
        
        Returns:
            整体统计信息字典
        """
        stats = {
            'timestamp': datetime.now().isoformat()
        }
        
        if self.db_tool:
            try:
                db_stats = self.db_tool.get_statistics()
                stats.update(db_stats)
            except Exception as e:
                stats['db_error'] = str(e)
        
        return stats


_analytics_tool_instance: Optional[AnalyticsTool] = None


def get_analytics_tool(db_tool=None) -> AnalyticsTool:
    """
    获取分析工具单例
    
    Args:
        db_tool: 数据库工具实例（可选）
        
    Returns:
        AnalyticsTool实例
    """
    global _analytics_tool_instance
    if _analytics_tool_instance is None:
        _analytics_tool_instance = AnalyticsTool(db_tool)
    return _analytics_tool_instance
