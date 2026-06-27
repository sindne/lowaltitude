"""
监控工具 - 使用psutil收集系统指标
"""
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class MonitoringTool:
    """监控工具 - 系统监控"""
    
    def __init__(self):
        self.metrics_history = []
        self.alerts = []
        self._api_call_count = 0
        self._response_times = []
        self._lock = threading.Lock()
        self._max_history = 100  # 保留最近100条历史记录
        
        # 告警阈值配置
        self.alert_thresholds = {
            'cpu_usage': 80.0,  # CPU使用率超过80%告警
            'memory_usage': 85.0,  # 内存使用率超过85%告警
            'disk_usage': 90.0,  # 磁盘使用率超过90%告警
            'response_time': 5.0,  # 响应时间超过5秒告警
        }
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        收集系统指标
        
        Returns:
            系统指标字典
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
        }
        
        if HAS_PSUTIL:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=0.5)
                metrics['cpu_usage'] = round(cpu_percent, 2)
                
                # 内存使用情况
                memory = psutil.virtual_memory()
                metrics['memory_usage'] = round(memory.percent, 2)
                metrics['memory_total'] = round(memory.total / (1024 ** 3), 2)  # GB
                metrics['memory_used'] = round(memory.used / (1024 ** 3), 2)  # GB
                metrics['memory_available'] = round(memory.available / (1024 ** 3), 2)  # GB
                
                # 磁盘使用情况
                disk = psutil.disk_usage('/')
                metrics['disk_usage'] = round(disk.percent, 2)
                metrics['disk_total'] = round(disk.total / (1024 ** 3), 2)  # GB
                metrics['disk_used'] = round(disk.used / (1024 ** 3), 2)  # GB
                metrics['disk_free'] = round(disk.free / (1024 ** 3), 2)  # GB
                
                # 网络IO
                net_io = psutil.net_io_counters()
                metrics['network_bytes_sent'] = net_io.bytes_sent
                metrics['network_bytes_recv'] = net_io.bytes_recv
                metrics['network_packets_sent'] = net_io.packets_sent
                metrics['network_packets_recv'] = net_io.packets_recv
                
                # 进程数
                metrics['process_count'] = len(list(psutil.process_iter()))
                
                # 系统启动时间
                boot_time = datetime.fromtimestamp(psutil.boot_time())
                metrics['system_uptime_seconds'] = int(time.time() - psutil.boot_time())
                metrics['system_boot_time'] = boot_time.isoformat()
                
            except Exception as e:
                metrics['error'] = f"收集系统指标失败: {str(e)}"
        else:
            metrics['warning'] = "psutil库未安装，部分指标不可用"
        
        # API调用统计
        with self._lock:
            metrics['api_calls'] = self._api_call_count
            
            # 平均响应时间
            if self._response_times:
                avg_response_time = sum(self._response_times) / len(self._response_times)
                metrics['average_response_time'] = round(avg_response_time, 3)
                metrics['min_response_time'] = round(min(self._response_times), 3)
                metrics['max_response_time'] = round(max(self._response_times), 3)
                metrics['response_time_samples'] = len(self._response_times)
            else:
                metrics['average_response_time'] = 0.0
                metrics['response_time_samples'] = 0
        
        # 保存到历史记录
        self._save_to_history(metrics)
        
        # 检查告警
        self._check_alerts(metrics)
        
        return metrics
    
    def _save_to_history(self, metrics: Dict[str, Any]) -> None:
        """保存指标到历史记录"""
        with self._lock:
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self._max_history:
                self.metrics_history.pop(0)
    
    def _check_alerts(self, metrics: Dict[str, Any]) -> None:
        """检查是否触发告警"""
        alerts = []
        
        # CPU使用率告警
        if 'cpu_usage' in metrics and metrics['cpu_usage'] > self.alert_thresholds['cpu_usage']:
            alerts.append({
                'type': 'high_cpu_usage',
                'severity': 'warning',
                'message': f"CPU使用率过高: {metrics['cpu_usage']}%",
                'timestamp': metrics['timestamp']
            })
        
        # 内存使用率告警
        if 'memory_usage' in metrics and metrics['memory_usage'] > self.alert_thresholds['memory_usage']:
            alerts.append({
                'type': 'high_memory_usage',
                'severity': 'warning',
                'message': f"内存使用率过高: {metrics['memory_usage']}%",
                'timestamp': metrics['timestamp']
            })
        
        # 磁盘使用率告警
        if 'disk_usage' in metrics and metrics['disk_usage'] > self.alert_thresholds['disk_usage']:
            alerts.append({
                'type': 'high_disk_usage',
                'severity': 'critical',
                'message': f"磁盘使用率过高: {metrics['disk_usage']}%",
                'timestamp': metrics['timestamp']
            })
        
        # 响应时间告警
        if 'average_response_time' in metrics and metrics['average_response_time'] > self.alert_thresholds['response_time']:
            alerts.append({
                'type': 'high_response_time',
                'severity': 'warning',
                'message': f"平均响应时间过长: {metrics['average_response_time']}s",
                'timestamp': metrics['timestamp']
            })
        
        # 添加到告警列表
        if alerts:
            with self._lock:
                self.alerts.extend(alerts)
                # 只保留最近50条告警
                if len(self.alerts) > 50:
                    self.alerts = self.alerts[-50:]
    
    def check_health(self) -> Dict[str, Any]:
        """
        检查系统健康状态
        
        Returns:
            健康状态字典
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }
        
        # 检查各服务状态
        services_to_check = ['api', 'database', 'vector_db', 'model']
        
        for service in services_to_check:
            # 这里可以添加实际的服务健康检查逻辑
            # 目前假设所有服务都在运行
            health['services'][service] = 'running'
        
        # 检查系统资源
        if HAS_PSUTIL:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                
                if cpu_percent > 90 or memory.percent > 95:
                    health['status'] = 'critical'
                elif cpu_percent > 70 or memory.percent > 80:
                    health['status'] = 'warning'
                    
            except Exception:
                pass
        
        return health
    
    def get_alerts(self, severity: Optional[str] = None, 
                    limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取告警信息
        
        Args:
            severity: 告警级别（可选）
            limit: 返回数量限制
            
        Returns:
            告警列表
        """
        with self._lock:
            alerts = self.alerts.copy()
        
        # 按严重级别过滤
        if severity:
            alerts = [alert for alert in alerts if alert.get('severity') == severity]
        
        # 按时间倒序排列并限制数量
        alerts.reverse()
        return alerts[:limit]
    
    def clear_alerts(self) -> int:
        """
        清除所有告警
        
        Returns:
            清除的告警数量
        """
        with self._lock:
            count = len(self.alerts)
            self.alerts.clear()
            return count
    
    def record_api_call(self, response_time: float) -> None:
        """
        记录API调用
        
        Args:
            response_time: 响应时间（秒）
        """
        with self._lock:
            self._api_call_count += 1
            self._response_times.append(response_time)
            # 只保留最近1000个响应时间
            if len(self._response_times) > 1000:
                self._response_times.pop(0)
    
    def reset_stats(self) -> None:
        """重置统计数据"""
        with self._lock:
            self._api_call_count = 0
            self._response_times.clear()
    
    def get_metrics_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取指标历史记录
        
        Args:
            limit: 返回数量限制
            
        Returns:
            指标历史列表
        """
        with self._lock:
            history = self.metrics_history.copy()
        
        history.reverse()
        return history[:limit]
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            系统信息字典
        """
        info = {
            "timestamp": datetime.now().isoformat()
        }
        
        if HAS_PSUTIL:
            try:
                # CPU信息
                info['cpu_count'] = psutil.cpu_count(logical=True)
                info['cpu_count_physical'] = psutil.cpu_count(logical=False)
                info['cpu_freq'] = psutil.cpu_freq().current if psutil.cpu_freq() else None
                
                # 操作系统信息
                import platform
                info['os_system'] = platform.system()
                info['os_release'] = platform.release()
                info['os_version'] = platform.version()
                info['machine'] = platform.machine()
                info['processor'] = platform.processor()
                
                # Python信息
                info['python_version'] = platform.python_version()
                
            except Exception as e:
                info['error'] = f"获取系统信息失败: {str(e)}"
        else:
            info['warning'] = "psutil库未安装，部分信息不可用"
        
        return info


_monitoring_tool_instance: Optional[MonitoringTool] = None


def get_monitoring_tool() -> MonitoringTool:
    """
    获取监控工具单例
    
    Returns:
        MonitoringTool实例
    """
    global _monitoring_tool_instance
    if _monitoring_tool_instance is None:
        _monitoring_tool_instance = MonitoringTool()
    return _monitoring_tool_instance
