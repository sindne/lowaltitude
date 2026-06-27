import os
import json
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.config import Config

class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or Config.DEEPSEEK_KEY
        self.base_url = base_url or "https://api.deepseek.com/v1"
        self.model = Config.DEEPSEEK_MODEL
        self.client = httpx.Client(timeout=120.0)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stream: bool = False
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "stream": stream
        }
        try:
            response = self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP error: {e.response.status_code} - {e.response.text}"
            print(f"DeepSeek API call failed: {error_detail}")
            raise Exception(error_detail) from e
        except Exception as e:
            print(f"DeepSeek API call failed: {str(e)}")
            raise
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        result = self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        if result.get("choices") and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        return ""
    
    def generate_structured_output(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        enhanced_system_prompt = "You are a professional data analyst. Please strictly output results in JSON format without any additional explanation."
        if system_prompt:
            enhanced_system_prompt = system_prompt + "\n\n" + enhanced_system_prompt
        response = self.generate_text(
            prompt=prompt,
            system_prompt=enhanced_system_prompt,
            temperature=temperature,
            max_tokens=4096
        )
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {str(e)}")
            print(f"Raw response: {response}")
            return {"raw_response": response, "error": str(e)}
    
    def test_connection(self) -> bool:
        try:
            response = self.generate_text(
                prompt="Please reply 'connection successful'",
                system_prompt="You are a test assistant",
                temperature=0.1,
                max_tokens=50
            )
            print(f"DeepSeek API connection test: {response}")
            return "successful" in response or "success" in response.lower()
        except Exception as e:
            print(f"DeepSeek API connection test failed: {str(e)}")
            return False
    
    def close(self):
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class LowAltitudeTrainingDataGenerator:
    def __init__(self, deepseek_client: Optional[DeepSeekClient] = None):
        self.client = deepseek_client or DeepSeekClient()
    
    def generate_risk_assessment_data(
        self,
        knowledge_context: str,
        num_samples: int = 10
    ) -> List[Dict[str, Any]]:
        system_prompt = "Generate risk assessment training data for low-altitude flight scenarios."
        prompt = f"Based on the following knowledge context, generate {num_samples} risk assessment samples:\n{knowledge_context}"
        result = self.client.generate_structured_output(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )
        if "raw_response" in result:
            return []
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            for key in result:
                if isinstance(result[key], list):
                    return result[key]
        return []
    
    def generate_conversation_data(
        self,
        knowledge_context: str,
        num_samples: int = 10
    ) -> List[Dict[str, Any]]:
        system_prompt = "Generate conversation training data for low-altitude flight scenarios."
        prompt = f"Based on the following knowledge context, generate {num_samples} conversation samples:\n{knowledge_context}"
        result = self.client.generate_structured_output(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )
        if "raw_response" in result:
            return []
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            for key in result:
                if isinstance(result[key], list):
                    return result[key]
        return []
    
    def generate_knowledge_extraction_data(
        self,
        raw_text: str,
        num_samples: int = 5
    ) -> List[Dict[str, Any]]:
        system_prompt = "Extract knowledge entities and relationships from the text."
        prompt = f"Extract {num_samples} knowledge samples from the following text:\n{raw_text}"
        result = self.client.generate_structured_output(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        if "raw_response" in result:
            return []
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            for key in result:
                if isinstance(result[key], list):
                    return result[key]
        return []
