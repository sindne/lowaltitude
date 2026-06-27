"""
本地 LLM 客户端 — LLaMA Factory API (OpenAI 兼容)

通过 LLaMA Factory 的 API 服务调用微调后的模型进行推理
"""
import sys
import os
import json
import urllib.request
from typing import Dict, List, Any, Optional, Generator

_LOCAL_PACKAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_local_packages"
)
if os.path.isdir(_LOCAL_PACKAGES_DIR) and _LOCAL_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _LOCAL_PACKAGES_DIR)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LLAMA_FACTORY_BASE_URL = "http://localhost:8000/v1"


class LocalLLMClient:
    """
    本地 LLM 客户端 — 通过 LLaMA Factory API 调用微调模型

    启动 API 服务:
        cd D:\\llama\\LlamaFactory-main\\LlamaFactory-main
        python src/llamafactory/api/app.py --model_name_or_path <model> --adapter_name_or_path <lora>
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "not-needed",
        model_name: str = "llama3-lora",
        timeout: int = 120
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self._available = False
        self._provider = "llama_factory"
        self._check_availability()

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def available(self) -> bool:
        return self._available

    def _try_connect(self, base_url: str) -> Optional[str]:
        try:
            url = f"{base_url}/models"
            req = urllib.request.Request(url)
            req.add_header('Authorization', f'Bearer {self.api_key}')
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode('utf-8'))
            if 'data' in data:
                models = [m.get('id', '') for m in data['data']]
                if models:
                    return models[0]
            elif 'object' in data and data.get('object') == 'list':
                models = [m.get('id', '') for m in data.get('data', [])]
                if models:
                    return models[0]
            return None
        except Exception:
            return None

    def _check_availability(self):
        if self._available:
            return

        model_id = self._try_connect(self.base_url)
        if model_id:
            self._available = True
            self.model_name = model_id
            print(f"[LocalLLM] LLaMA Factory API 可用: {model_id} ({self.base_url})")
            return

        print(f"[LocalLLM] LLaMA Factory API 不可用: {self.base_url}")
        print(f"  请启动 API 服务: cd D:\\llama\\LlamaFactory-main\\LlamaFactory-main && python src/llamafactory/api/app.py")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None

        try:
            data = {
                'model': self.model_name,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens
            }

            url = f"{self.base_url}/chat/completions"
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                }
            )

            resp = urllib.request.urlopen(req, timeout=self.timeout)
            result = json.loads(resp.read().decode('utf-8'))
            return result

        except Exception as e:
            print(f"[LocalLLM] 请求失败: {e}")
            return None

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        result = self.chat(messages, temperature, max_tokens)
        if result and 'choices' in result:
            return result['choices'][0]['message']['content']
        return ""

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        if not self._available:
            yield "[LLaMA Factory API 不可用]"
            return

        try:
            data = {
                'model': self.model_name,
                'messages': messages,
                'temperature': 0.3,
                'max_tokens': 2048,
                'stream': True
            }

            url = f"{self.base_url}/chat/completions"
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                }
            )

            resp = urllib.request.urlopen(req, timeout=self.timeout)
            buffer = b""
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    line = line.strip()
                    if line.startswith(b'data: '):
                        line = line[6:]
                        if line == b'[DONE]':
                            return
                        try:
                            data = json.loads(line)
                            choices = data.get('choices', [])
                            if choices:
                                delta = choices[0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            yield f"[流式生成出错: {e}]"

    def generate_risk_report(
        self,
        city_name: str,
        graph_context: Dict[str, Any],
        sora_result: Optional[Dict[str, Any]] = None,
        extra_context: str = ""
    ) -> str:
        summary = graph_context.get('summary', '')
        entities = graph_context.get('subgraph', {}).get('entities', [])
        relations = graph_context.get('subgraph', {}).get('relations', [])
        risk_factors = graph_context.get('risk_factors', [])
        infrastructure = graph_context.get('infrastructure', [])
        sensitive_areas = graph_context.get('sensitive_areas', [])
        engine = graph_context.get('engine', 'memory')

        system_prompt = """你是一个低空空域风险评估专家。请基于提供的知识图谱上下文，生成专业、详细的风险评估报告。
报告应包含：
1. 区域概况
2. 风险因素分析（结合知识图谱中的实体和关系）
3. 基础设施与敏感区域影响
4. SORA框架评估结果（如有）
5. 飞行安全建议
使用中文回答，语言专业但易懂。"""

        user_prompt_parts = [f"请基于以下知识图谱信息，为 {city_name} 生成风险评估报告。"]
        user_prompt_parts.append(f"知识引擎: {engine}")

        if summary:
            user_prompt_parts.append(f"\n## 知识图谱摘要\n{summary}")

        if risk_factors:
            user_prompt_parts.append(f"\n## 风险因素 ({len(risk_factors)} 个)")
            user_prompt_parts.append(self._format_factors(risk_factors))

        if infrastructure:
            user_prompt_parts.append(f"\n## 基础设施 ({len(infrastructure)} 个)")
            user_prompt_parts.append(self._format_entities(infrastructure))

        if sensitive_areas:
            user_prompt_parts.append(f"\n## 敏感区域 ({len(sensitive_areas)} 个)")
            user_prompt_parts.append(self._format_entities(sensitive_areas))

        user_prompt_parts.append(f"\n## 图谱统计")
        user_prompt_parts.append(f"- 总实体数: {len(entities)}")
        user_prompt_parts.append(f"- 总关系数: {len(relations)}")

        if extra_context:
            user_prompt_parts.append(f"\n{extra_context}")

        user_prompt_parts.append("\n请生成完整报告。")

        return self.generate("\n".join(user_prompt_parts), system_prompt, temperature=0.3)

    def _format_factors(self, factors: List[Dict]) -> str:
        lines = []
        for f in factors:
            name = f.get('name', f.get('title', ''))
            props = f.get('properties', {})
            weight = props.get('weight', 0)
            value = props.get('value', 0)
            lines.append(f"- {name}: 权重={weight:.1f}%, 风险值={value:.2f}")
        return '\n'.join(lines)

    def _format_entities(self, entities: List[Dict]) -> str:
        lines = []
        for e in entities[:10]:
            name = e.get('name', e.get('title', ''))
            props = e.get('properties', {})
            details = ', '.join(
                f"{k}={v}" for k, v in props.items()
                if k in ('infra_type', 'area_type', 'priority')
            )
            line = f"- {name}"
            if details:
                line += f" ({details})"
            lines.append(line)
        if len(entities) > 10:
            lines.append(f"... 共 {len(entities)} 个")
        return '\n'.join(lines)


_local_llm: Optional[LocalLLMClient] = None


def get_local_llm(
    base_url: str = "http://localhost:8000/v1",
    model_name: str = "llama3-lora"
) -> LocalLLMClient:
    global _local_llm
    if _local_llm is None:
        _local_llm = LocalLLMClient(
            base_url=base_url,
            model_name=model_name
        )
    elif not _local_llm.available:
        _local_llm._check_availability()
    return _local_llm


def reset_local_llm():
    global _local_llm
    _local_llm = None