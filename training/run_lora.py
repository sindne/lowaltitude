"""
LoRA 微调训练脚本 - 命令行入口
基于 LLaMA Factory 的微调实现

用法:
    python run_lora.py --base_model Qwen/Qwen2.5-0.5B --data_path ./data/training.json --output_dir ./output
"""
import os
import sys
import json
import argparse
import subprocess

_LOCAL_PACKAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_local_packages"
)
if os.path.isdir(_LOCAL_PACKAGES_DIR) and _LOCAL_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _LOCAL_PACKAGES_DIR)

_LLAMA_FACTORY_PATH = r"D:\llama\LlamaFactory-main\LlamaFactory-main"
_LLAMA_FACTORY_SRC = os.path.join(_LLAMA_FACTORY_PATH, "src")
if os.path.isdir(_LLAMA_FACTORY_SRC) and _LLAMA_FACTORY_SRC not in sys.path:
    sys.path.insert(0, _LLAMA_FACTORY_SRC)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_args():
    parser = argparse.ArgumentParser(description="LoRA Fine-tuning Script (LLaMA Factory)")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-0.5B",
                        help="基础模型名称或路径")
    parser.add_argument("--data_path", type=str, required=True,
                        help="训练数据 JSON 文件路径")
    parser.add_argument("--output_dir", type=str, default="./training/output",
                        help="输出目录")
    parser.add_argument("--lora_rank", type=int, default=8,
                        help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=16,
                        help="LoRA alpha")
    parser.add_argument("--lora_dropout", type=float, default=0.05,
                        help="LoRA dropout")
    parser.add_argument("--learning_rate", type=float, default=2e-4,
                        help="学习率")
    parser.add_argument("--num_epochs", type=int, default=3,
                        help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=4,
                        help="批次大小")
    parser.add_argument("--max_seq_length", type=int, default=2048,
                        help="最大序列长度")
    return parser.parse_args()


def _check_llama_factory_available() -> bool:
    launcher = os.path.join(_LLAMA_FACTORY_SRC, "llamafactory", "launcher.py")
    return os.path.isdir(_LLAMA_FACTORY_PATH) and os.path.isfile(launcher)


def _prepare_llama_factory_dataset(data_path, output_dir):
    dataset_dir = os.path.join(output_dir, "dataset")
    os.makedirs(dataset_dir, exist_ok=True)

    with open(data_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    if isinstance(raw_data, list):
        samples = raw_data
    elif isinstance(raw_data, dict):
        samples = raw_data.get("data", raw_data.get("samples", raw_data.get("cases", [])))
        if not samples:
            samples = raw_data.get("conversations", [])
    else:
        samples = []

    alpaca_data = []
    for sample in samples:
        if isinstance(sample, str):
            alpaca_data.append({"instruction": "", "input": "", "output": sample})
        elif isinstance(sample, dict):
            instruction = sample.get("instruction", sample.get("prompt", ""))
            input_text = sample.get("input", sample.get("context", ""))
            output = sample.get("output", sample.get("response", ""))
            if not output:
                messages = sample.get("messages", [])
                assistant_msgs = [m.get("content", "") for m in messages if m.get("role") == "assistant"]
                output = assistant_msgs[-1] if assistant_msgs else ""
            alpaca_data.append({
                "instruction": instruction or "",
                "input": input_text or "",
                "output": output or ""
            })

    dataset_name = "low_altitude_risk"
    dataset_file = os.path.join(dataset_dir, f"{dataset_name}.json")
    with open(dataset_file, 'w', encoding='utf-8') as f:
        json.dump(alpaca_data, f, ensure_ascii=False, indent=2)

    dataset_info = {dataset_name: {"file_name": f"{dataset_name}.json"}}
    info_path = os.path.join(dataset_dir, "dataset_info.json")
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(dataset_info, f, ensure_ascii=False, indent=2)

    print(f"[run_lora] LLaMA Factory 数据集已准备: {dataset_file} ({len(alpaca_data)} 条)")
    return dataset_name, dataset_dir


def _run_llama_factory_training(args, output_dir):
    dataset_name, dataset_dir = _prepare_llama_factory_dataset(args.data_path, output_dir)

    yaml_config = f"""### model
model_name_or_path: {args.base_model}
trust_remote_code: true

### method
stage: sft
do_train: true
finetuning_type: lora
lora_rank: {args.lora_rank}
lora_alpha: {args.lora_alpha}
lora_dropout: {args.lora_dropout}
lora_target: all

### dataset
dataset: {dataset_name}
template: qwen
cutoff_len: {args.max_seq_length}
overwrite_cache: true
preprocessing_num_workers: 2
dataset_dir: {dataset_dir.replace(chr(92), '/')}

### output
output_dir: {output_dir.replace(chr(92), '/')}
logging_steps: 10
save_steps: 500
plot_loss: false
overwrite_output_dir: true
save_only_model: false
report_to: none

### train
per_device_train_batch_size: {args.batch_size}
gradient_accumulation_steps: 1
learning_rate: {args.learning_rate}
num_train_epochs: {args.num_epochs}
lr_scheduler_type: cosine
warmup_ratio: 0.1
fp16: true

### eval
val_size: 0.0
"""

    yaml_path = os.path.join(output_dir, "train_config.yaml")
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_config)

    cli_script = os.path.join(_LLAMA_FACTORY_SRC, "llamafactory", "launcher.py")
    cmd = [sys.executable, cli_script, "train", yaml_path]

    print(f"[run_lora] LLaMA Factory 训练启动: {' '.join(cmd)}")
    print(f"[run_lora] 基础模型: {args.base_model}")

    env = os.environ.copy()
    env["FORCE_TORCHRUN"] = "0"

    result = subprocess.run(
        cmd, cwd=_LLAMA_FACTORY_PATH, env=env,
        capture_output=True, text=True, timeout=7200
    )

    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            if any(kw in line.lower() for kw in ['loss', 'step', 'epoch', 'error', 'completed']):
                print(f"[run_lora] {line.strip()}")

    if result.returncode != 0:
        print(f"[run_lora] LLaMA Factory 训练退出码: {result.returncode}")
        if result.stderr:
            print(f"[run_lora] stderr: {result.stderr[:500]}")

    return result.returncode


def main():
    args = parse_args()

    if not _check_llama_factory_available():
        print(f"[run_lora] 错误: LLaMA Factory 不可用！")
        print(f"  请确保 LLaMA Factory 已安装于: {_LLAMA_FACTORY_PATH}")
        print(f"  下载地址: https://github.com/hiyouga/LLaMA-Factory")
        sys.exit(1)

    print(f"[run_lora] 使用 LLaMA Factory 后端训练")
    os.makedirs(args.output_dir, exist_ok=True)
    ret = _run_llama_factory_training(args, args.output_dir)
    if ret == 0:
        print(f"[run_lora] LLaMA Factory 训练完成! 输出目录: {args.output_dir}")
    else:
        print(f"[run_lora] LLaMA Factory 训练失败 (退出码: {ret})")
        sys.exit(1)


if __name__ == "__main__":
    main()