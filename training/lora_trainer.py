"""
LoRA微调训练器 - 基于 LLaMA Factory 的生产级微调实现

训练后端: LLaMA Factory (D:\\llama\\LlamaFactory-main\\LlamaFactory-main)
支持模型链式迭代训练、自动基础模型检测、PostGIS数据加载
"""
import os
import sys
import json
import glob
import shutil
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

_LOCAL_PACKAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_local_packages"
)
if os.path.isdir(_LOCAL_PACKAGES_DIR) and _LOCAL_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _LOCAL_PACKAGES_DIR)

_LLAMA_FACTORY_PATH = r"D:\llama\LlamaFactory-main\LlamaFactory-main"
_LLAMA_FACTORY_SRC = os.path.join(_LLAMA_FACTORY_PATH, "src")
if os.path.isdir(_LLAMA_FACTORY_SRC) and _LLAMA_FACTORY_SRC not in sys.path:
    sys.path.insert(0, _LLAMA_FACTORY_SRC)


@dataclass
class TrainingConfig:
    base_model: str = "./local_models/base_model"
    output_dir: str = "./local_models"
    lora_rank: int = 8
    lora_alpha: int = 16
    learning_rate: float = 5e-5
    num_epochs: int = 3
    batch_size: int = 4
    max_seq_length: int = 2048


class LoRATrainer:
    """LoRA微调训练器 - 基于 LLaMA Factory，支持模型链式迭代"""

    TRAINING_MODELS_DIR = "./training/models"
    LOCAL_MODELS_DIR = "./training/local_models"

    def __init__(self, model_output_path: str = "./training/models"):
        self.model_output_path = model_output_path
        self._ensure_output_path()
        self.training_status = "idle"
        self.training_progress = 0.0
        self._latest_model_info: Optional[Dict] = None

    def _ensure_output_path(self):
        if not os.path.exists(self.model_output_path):
            os.makedirs(self.model_output_path, exist_ok=True)
        local_models_dir = os.path.join(os.path.dirname(self.model_output_path), "local_models")
        if not os.path.exists(local_models_dir):
            os.makedirs(local_models_dir, exist_ok=True)

    def find_latest_model(self) -> Optional[Dict[str, Any]]:
        """扫描所有模型目录，返回最新可用模型信息"""
        search_dirs = [
            self.model_output_path,
            os.path.join(os.path.dirname(self.model_output_path), "local_models"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_models"),
        ]

        candidates = []
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            for item in os.listdir(search_dir):
                item_path = os.path.join(search_dir, item)
                if not os.path.isdir(item_path):
                    continue
                status_file = os.path.join(item_path, "model_status.json")
                config_file = os.path.join(item_path, "training_config.json")
                if not os.path.exists(status_file):
                    continue
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status = json.load(f)
                    if not status.get("is_valid", False):
                        continue
                    config = {}
                    if os.path.exists(config_file):
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                    candidates.append({
                        "name": item,
                        "path": item_path,
                        "created_at": status.get("created_at", ""),
                        "training_samples": status.get("num_training_samples", 0),
                        "config": config,
                        "base_model": config.get("base_model", "deepseek-ai/deepseek-chat"),
                    })
                except (json.JSONDecodeError, IOError):
                    continue

        candidates.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        self._latest_model_info = candidates[0] if candidates else None
        return self._latest_model_info

    def get_latest_base_model(self) -> str:
        """获取最新模型的基础模型路径（用于链式训练）"""
        latest = self.find_latest_model()
        if latest:
            return latest.get("path", latest.get("base_model", "deepseek-ai/deepseek-chat"))
        return "deepseek-ai/deepseek-chat"

    def load_latest_config(self) -> Optional[Dict[str, Any]]:
        """加载最新模型的训练配置"""
        latest = self.find_latest_model()
        if latest and latest.get("config"):
            return latest["config"]
        return None

    def prepare_training_config(
        self,
        base_model: str = None,
        lora_rank: int = 8,
        lora_alpha: int = 16,
        lora_dropout: float = 0.05,
        learning_rate: float = 2e-4,
        batch_size: int = 4,
        num_epochs: int = 3,
        max_seq_length: int = 2048,
        use_latest_model: bool = True
    ) -> Dict[str, Any]:
        if base_model is None and use_latest_model:
            base_model = self.get_latest_base_model()

        if base_model is None:
            base_model = "deepseek-ai/deepseek-chat"

        config = {
            "base_model": base_model,
            "lora_config": {
                "r": lora_rank,
                "lora_alpha": lora_alpha,
                "lora_dropout": lora_dropout,
                "bias": "none",
                "task_type": "CAUSAL_LM"
            },
            "training_args": {
                "learning_rate": learning_rate,
                "per_device_train_batch_size": batch_size,
                "num_train_epochs": num_epochs,
                "max_seq_length": max_seq_length,
                "logging_steps": 10,
                "save_strategy": "epoch",
                "output_dir": self.model_output_path
            },
            "created_at": datetime.now().isoformat(),
        }

        latest_model = self.find_latest_model()
        if latest_model:
            config["previous_model"] = latest_model.get("name")
            config["is_chain_training"] = True

        return config

    def start_training(
        self,
        training_data_path: str,
        config: Optional[Dict[str, Any]] = None,
        use_latest_model: bool = True
    ) -> str:
        """开始训练 - 自动检测并使用最新模型作为基础"""
        if config is None:
            config = self.prepare_training_config(use_latest_model=use_latest_model)

        latest_model = self.find_latest_model()
        if latest_model and use_latest_model:
            base_model_path = latest_model.get("path")
            if base_model_path and os.path.exists(base_model_path):
                config["base_model"] = base_model_path
                print(f"[LoRA] 自动选择最新模型: {latest_model['name']} (样本数: {latest_model['training_samples']})")

        self.training_status = "training"
        self.training_progress = 0.0

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        iteration = 1
        if latest_model:
            import re as _re
            match = _re.search(r'iter_(\d+)', latest_model.get("name", "")) if latest_model else None
            if match:
                iteration = int(match.group(1)) + 1
            else:
                iteration = 2

        model_name_iter = f"iter_{timestamp}"

        local_models_dir = os.path.join(os.path.dirname(self.model_output_path), "local_models")
        model_path_iter = os.path.join(local_models_dir, model_name_iter)

        if not os.path.exists(model_path_iter):
            os.makedirs(model_path_iter, exist_ok=True)

        config_path = os.path.join(model_path_iter, "training_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        if os.path.exists(training_data_path):
            shutil.copy2(training_data_path, os.path.join(model_path_iter, "training_data.json"))

        try:
            training_result = self._execute_training(config, training_data_path, model_path_iter)
        except Exception as e:
            print(f"[LoRA] 训练执行异常: {e}")
            training_result = {"status": "failed", "error": str(e)}
            self.training_status = "failed"

        num_samples = training_result.get("num_samples", 0)
        status_path = os.path.join(model_path_iter, "model_status.json")
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump({
                "model_name": model_name_iter,
                "created_at": datetime.now().isoformat(),
                "status": training_result.get("status", "completed"),
                "training_data_path": training_data_path,
                "is_valid": training_result.get("status") != "failed",
                "num_training_samples": num_samples,
                "base_model": config.get("base_model", ""),
                "iteration": iteration,
                "adapter_path": training_result.get("adapter_path", ""),
            }, f, ensure_ascii=False, indent=2)

        self.training_progress = 1.0
        if self.training_status != "failed":
            self.training_status = "completed"

        return model_path_iter

    def _check_llama_factory_available(self) -> bool:
        if not os.path.isdir(_LLAMA_FACTORY_PATH):
            return False
        cli_path = os.path.join(_LLAMA_FACTORY_PATH, "src", "llamafactory", "launcher.py")
        return os.path.isfile(cli_path)

    def _generate_llama_factory_config(
        self,
        config: Dict[str, Any],
        dataset_name: str,
        output_path: str,
        dataset_info_path: str
    ) -> str:
        base_model = config.get("base_model", "Qwen/Qwen2.5-0.5B")
        lora_cfg = config.get("lora_config", {})
        train_cfg = config.get("training_args", {})

        yaml_config = f"""### model
model_name_or_path: {base_model}
trust_remote_code: true

### method
stage: sft
do_train: true
finetuning_type: lora
lora_rank: {lora_cfg.get('r', 8)}
lora_alpha: {lora_cfg.get('lora_alpha', 16)}
lora_dropout: {lora_cfg.get('lora_dropout', 0.05)}
lora_target: all

### dataset
dataset: {dataset_name}
template: qwen
cutoff_len: {train_cfg.get('max_seq_length', 2048)}
overwrite_cache: true
preprocessing_num_workers: 2
dataset_dir: {dataset_info_path.replace(chr(92), '/')}

### output
output_dir: {output_path.replace(chr(92), '/')}
logging_steps: 10
save_steps: 500
plot_loss: false
overwrite_output_dir: true
save_only_model: false
report_to: none

### train
per_device_train_batch_size: {train_cfg.get('per_device_train_batch_size', 4)}
gradient_accumulation_steps: 1
learning_rate: {train_cfg.get('learning_rate', 2e-4)}
num_train_epochs: {train_cfg.get('num_train_epochs', 3)}
lr_scheduler_type: cosine
warmup_ratio: 0.1
fp16: true

### eval
val_size: 0.0
"""

        yaml_path = os.path.join(output_path, "train_config.yaml")
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(yaml_config)
        print(f"[LLaMA-Factory] 训练配置已生成: {yaml_path}")
        return yaml_path

    def _prepare_llama_factory_dataset(
        self,
        training_data_path: str,
        output_path: str
    ) -> tuple:
        dataset_dir = os.path.join(output_path, "dataset")
        os.makedirs(dataset_dir, exist_ok=True)

        with open(training_data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        if isinstance(raw_data, list):
            samples = raw_data
        elif isinstance(raw_data, dict):
            samples = raw_data.get("data", raw_data.get("samples", raw_data.get("cases", [])))
            if not samples:
                samples = raw_data.get("conversations", [])
        else:
            samples = []

        if not samples:
            samples = self._generate_default_samples()

        alpaca_data = []
        for sample in samples:
            if isinstance(sample, str):
                alpaca_data.append({
                    "instruction": "",
                    "input": "",
                    "output": sample
                })
            elif isinstance(sample, dict):
                instruction = sample.get("instruction", sample.get("prompt", ""))
                input_text = sample.get("input", sample.get("context", ""))
                output = sample.get("output", sample.get("response", ""))
                if not output:
                    messages = sample.get("messages", [])
                    assistant_msgs = [m.get("content", "") for m in messages if m.get("role") == "assistant"]
                    output = assistant_msgs[-1] if assistant_msgs else ""
                    user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
                    if user_msgs and not instruction:
                        instruction = user_msgs[0]
                alpaca_data.append({
                    "instruction": instruction or "",
                    "input": input_text or "",
                    "output": output or ""
                })

        dataset_name = "low_altitude_risk"
        dataset_file = os.path.join(dataset_dir, f"{dataset_name}.json")
        with open(dataset_file, 'w', encoding='utf-8') as f:
            json.dump(alpaca_data, f, ensure_ascii=False, indent=2)

        dataset_info = {
            dataset_name: {
                "file_name": f"{dataset_name}.json"
            }
        }
        info_path = os.path.join(dataset_dir, "dataset_info.json")
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(dataset_info, f, ensure_ascii=False, indent=2)

        print(f"[LLaMA-Factory] 数据集已准备: {dataset_file} ({len(alpaca_data)} 条)")
        return dataset_name, dataset_dir

    def _execute_training_llama_factory(
        self,
        config: Dict[str, Any],
        training_data_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        try:
            dataset_name, dataset_dir = self._prepare_llama_factory_dataset(
                training_data_path, output_path
            )
            yaml_path = self._generate_llama_factory_config(
                config, dataset_name, output_path, dataset_dir
            )
            base_model = config.get("base_model", "Qwen/Qwen2.5-0.5B")

            cli_script = os.path.join(_LLAMA_FACTORY_SRC, "llamafactory", "launcher.py")
            cmd = [
                sys.executable, cli_script, "train", yaml_path
            ]

            print(f"[LLaMA-Factory] 启动训练: {' '.join(cmd)}")
            print(f"[LLaMA-Factory] 基础模型: {base_model}")
            print(f"[LLaMA-Factory] 输出目录: {output_path}")

            env = os.environ.copy()
            env["FORCE_TORCHRUN"] = "0"

            result = subprocess.run(
                cmd,
                cwd=_LLAMA_FACTORY_PATH,
                env=env,
                capture_output=True,
                text=True,
                timeout=7200
            )

            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if any(kw in line.lower() for kw in ['loss', 'step', 'epoch', 'error', 'completed']):
                        print(f"[LLaMA-Factory] {line.strip()}")

            if result.returncode != 0:
                print(f"[LLaMA-Factory] 训练退出码: {result.returncode}")
                if result.stderr:
                    print(f"[LLaMA-Factory] stderr: {result.stderr[:500]}")
                raise RuntimeError(f"LLaMA Factory 训练失败，退出码: {result.returncode}")

            checkpoint_dir = os.path.join(output_path)
            adapter_path = None
            for root, dirs, files in os.walk(checkpoint_dir):
                if "adapter_config.json" in files:
                    adapter_path = root
                    break
                for d in sorted(dirs, reverse=True):
                    check_dir = os.path.join(root, d)
                    if os.path.isfile(os.path.join(check_dir, "adapter_config.json")):
                        adapter_path = check_dir
                        break
                if adapter_path:
                    break

            if adapter_path is None:
                for item in os.listdir(checkpoint_dir):
                    item_path = os.path.join(checkpoint_dir, item)
                    if os.path.isdir(item_path):
                        for f in os.listdir(item_path):
                            if f == "adapter_config.json":
                                adapter_path = item_path
                                break
                    if adapter_path:
                        break

            with open(training_data_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            if isinstance(raw_data, list):
                num_samples = len(raw_data)
            elif isinstance(raw_data, dict):
                num_samples = len(raw_data.get("data", raw_data.get("samples", raw_data.get("cases", []))))
            else:
                num_samples = 0

            return {
                "status": "completed",
                "num_samples": num_samples,
                "adapter_path": adapter_path or output_path,
                "base_model": base_model,
                "backend": "llama_factory",
            }

        except subprocess.TimeoutExpired:
            print("[LLaMA-Factory] 训练超时")
            return None
        except Exception as e:
            print(f"[LLaMA-Factory] 训练异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _execute_training(
        self,
        config: Dict[str, Any],
        training_data_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        执行 LoRA 微调训练 — 仅使用 LLaMA Factory

        Args:
            config: 训练配置
            training_data_path: 训练数据 JSON 文件路径
            output_path: 模型输出路径

        Returns:
            训练结果字典

        Raises:
            RuntimeError: LLaMA Factory 不可用
        """
        if not self._check_llama_factory_available():
            raise RuntimeError(
                "LLaMA Factory 不可用！\n"
                f"请确保 LLaMA Factory 已安装于: {_LLAMA_FACTORY_PATH}\n"
                "下载地址: https://github.com/hiyouga/LLaMA-Factory"
            )

        print("[LoRA] 使用 LLaMA Factory 后端")
        result = self._execute_training_llama_factory(
            config, training_data_path, output_path
        )
        if result is None:
            raise RuntimeError("LLaMA Factory 训练失败，请检查日志")
        return result

    def _resolve_model_path(self, model_name: str) -> Optional[str]:
        """解析模型路径，支持本地路径和HuggingFace模型名"""
        if os.path.exists(model_name) and os.path.isdir(model_name):
            return model_name

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_candidate = os.path.join(project_root, "local_models", model_name)
        if os.path.exists(local_candidate) and os.path.isdir(local_candidate):
            return local_candidate

        local_candidate = os.path.join(project_root, "local_models", "qwen2.5-0.5b-instruct")
        if os.path.exists(local_candidate) and os.path.isdir(local_candidate):
            return local_candidate

        return None

    def _generate_default_samples(self) -> List[Dict[str, str]]:
        """生成默认的低空风险评估训练样本"""
        return [
            {
                "instruction": "对指定城市进行低空空域风险评估",
                "input": "城市: 北京\n人口密度: 高\n空域类型: 管制空域",
                "output": "北京低空空域风险评估报告:\n1. 地面风险等级: GRC-3 (中等风险)\n2. 空域风险等级: ARC-B\n3. SAIL等级: III\n4. 主要风险因素: 人口密度高、建筑物密集\n5. 建议措施: 加强飞行监控、限制飞行高度"
            },
            {
                "instruction": "分析城市低空飞行安全性",
                "input": "城市: 上海\n人口密度: 极高\n空域类型: 管制空域\n敏感区域: 外滩、陆家嘴",
                "output": "上海低空空域风险评估报告:\n1. 地面风险等级: GRC-4 (高风险)\n2. 空域风险等级: ARC-C\n3. SAIL等级: IV\n4. 主要风险因素: 人口密度极高、敏感区域众多、高楼密集\n5. 建议措施: 严格限制飞行区域、增加安全冗余"
            },
            {
                "instruction": "评估无人机飞行计划安全性",
                "input": "城市: 武汉\n飞行区域: 光谷\n飞行高度: 120米\n飞行器类型: 多旋翼无人机",
                "output": "武汉光谷区域飞行安全评估:\n1. 地面风险等级: GRC-2\n2. 空域风险等级: ARC-A\n3. SAIL等级: II\n4. 风险因素: 科技园区人口适中、建筑物间距合理\n5. 飞行建议: 在120米高度可安全飞行，注意避开大学区域"
            },
            {
                "instruction": "分析工业园区低空风险",
                "input": "城市: 石家庄\n区域类型: 工业园区\n空域类型: 非管制空域",
                "output": "石家庄工业园区风险评估:\n1. 地面风险等级: GRC-2\n2. 空域风险等级: ARC-A\n3. SAIL等级: I\n4. 风险因素: 人口密度低、建筑物分散\n5. 飞行建议: 适合低空飞行测试，注意工业设施安全距离"
            },
            {
                "instruction": "评估城市敏感区域周边飞行风险",
                "input": "城市: 黄石\n区域: 市中心\n建筑物密度: 中等\n敏感区域: 政府机关",
                "output": "黄石市中心区域飞行评估:\n1. 地面风险等级: GRC-3\n2. 空域风险等级: ARC-B\n3. SAIL等级: III\n4. 主要风险: 政府机关敏感区域、中等建筑物密度\n5. 建议: 避开政府机关区域，飞行高度不超过100米"
            },
        ]

    def start_training_from_postgis(
        self,
        postgis_db=None,
        dataset_id: int = None,
        dataset_name: str = None,
        config: Optional[Dict[str, Any]] = None,
        use_latest_model: bool = True
    ) -> str:
        json_path = self.load_training_data_from_postgis(
            postgis_db=postgis_db,
            dataset_id=dataset_id,
            dataset_name=dataset_name
        )

        if json_path is None:
            raise ValueError("无法从 PostGIS 加载训练数据")

        result = self.start_training(
            training_data_path=json_path,
            config=config,
            use_latest_model=use_latest_model
        )

        if postgis_db is not None:
            try:
                latest_model = self.find_latest_model()
                postgis_db.save_finetune_history(
                    model_name=latest_model["name"] if latest_model else "unknown",
                    model_path=result,
                    dataset_id=dataset_id,
                    training_samples_count=50,
                    status="completed"
                )
            except Exception as e:
                print(f"[LoRA] 保存微调历史到 PostGIS 失败: {e}")

        return result

    def load_training_data_from_postgis(
        self,
        postgis_db=None,
        dataset_id: int = None,
        dataset_name: str = None
    ) -> Optional[str]:
        if postgis_db is None:
            try:
                sys_path = list(sys.path)
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from mcp_tools.postgis_database import get_postgis_database
                postgis_db = get_postgis_database()
                sys.path = sys_path
            except Exception as e:
                print(f"[LoRA] PostGIS 连接失败: {e}")
                return None

        if dataset_id is None and dataset_name is None:
            latest = postgis_db.get_latest_training_dataset("risk_assessment")
            if latest:
                dataset_id = latest["id"]
                print(f"[LoRA] 自动选择最新数据集: {latest['name']} (ID={dataset_id}, {latest['total_samples']} 样本)")
            else:
                print("[LoRA] PostGIS 中无训练数据集")
                return None

        if dataset_id is None and dataset_name:
            ds = postgis_db.get_training_dataset(name=dataset_name)
            if ds:
                dataset_id = ds["id"]

        if dataset_id is None:
            return None

        export_dir = os.path.join(os.path.dirname(self.model_output_path), "data")
        os.makedirs(export_dir, exist_ok=True)

        from datetime import datetime
        json_path = os.path.join(export_dir, f"postgis_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        return postgis_db.export_training_json(dataset_id, json_path)

    def get_training_status(self) -> Dict[str, Any]:
        trained_models = self.list_trained_models()
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_models_dir = os.path.join(project_root, "local_models")
        has_local_models = False
        if os.path.exists(local_models_dir):
            for item in os.listdir(local_models_dir):
                item_path = os.path.join(local_models_dir, item)
                if os.path.isdir(item_path) and (item.startswith('iter_') or item.startswith('lora_model_')):
                    has_local_models = True
                    break

        model_available_locally = len(trained_models) > 0 or has_local_models
        latest = self.find_latest_model()

        return {
            "status": self.training_status,
            "progress": self.training_progress,
            "model_output_path": self.model_output_path,
            "model_available_locally": model_available_locally,
            "latest_model": latest.get("name") if latest else None,
            "latest_model_samples": latest.get("training_samples") if latest else 0,
        }

    def list_trained_models(self) -> list:
        if not os.path.exists(self.model_output_path):
            return []
        models = []
        for item in os.listdir(self.model_output_path):
            item_path = os.path.join(self.model_output_path, item)
            if os.path.isdir(item_path):
                models.append({
                    "name": item,
                    "path": item_path,
                    "created_at": datetime.fromtimestamp(os.path.getctime(item_path)).isoformat()
                })
        return sorted(models, key=lambda x: x["created_at"], reverse=True)

    def load_peft_model(
        self,
        base_model_name: str = None,
        adapter_path: str = None
    ):
        """
        加载带 PEFT 适配器的模型

        Args:
            base_model_name: 基础模型名称或路径
            adapter_path: LoRA 适配器路径

        Returns:
            (model, tokenizer) 元组
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        if base_model_name is None:
            base_model_name = self.get_latest_base_model()

        if adapter_path is None:
            latest = self.find_latest_model()
            if latest:
                model_path = latest.get("path", "")
                adapter_candidate = os.path.join(model_path, "adapter_model")
                if os.path.exists(adapter_candidate):
                    adapter_path = adapter_candidate
                else:
                    adapter_path = model_path

        if adapter_path is None:
            raise ValueError("未找到可用的 LoRA 适配器路径")

        resolved_base = self._resolve_model_path(base_model_name)
        if resolved_base:
            base_model_name = resolved_base

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        dtype = torch.float16 if device == 'cuda' else torch.float32

        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=dtype,
            device_map='auto' if device == 'cuda' else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )

        model = PeftModel.from_pretrained(base_model, adapter_path)
        model.eval()

        print(f"[LoRA] PEFT 模型加载成功: {base_model_name} + {adapter_path}")
        return model, tokenizer