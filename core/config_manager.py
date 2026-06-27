import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file or '.env'
        self._load_config()
        self._set_defaults()
    
    def _load_config(self):
        load_dotenv(self.env_file)
    
    def _set_defaults(self):
        defaults = {
            'PORT': '5006',
            'DEBUG': 'false',
            'LOG_LEVEL': 'INFO',
            'BASE_MODEL_NAME': 'gpt2',
            'MODEL_OUTPUT_DIR': './local_models',
            'HF_ENDPOINT': 'https://hf-mirror.com',
            'API_CACHE_TTL': '3600',
            'ENABLE_CACHE': 'true'
        }
        for key, value in defaults.items():
            if key not in os.environ:
                os.environ[key] = value
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key)
        return int(value) if value else default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self.get(key)
        return float(value) if value else default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        return value.lower() in ('true', '1', 'yes') if value else default
    
    @property
    def amap_key(self) -> Optional[str]:
        return self.get('AMAP_KEY')
    
    @property
    def baidu_map_key(self) -> Optional[str]:
        return self.get('BAIDU_MAP_KEY')
    
    @property
    def tencent_map_key(self) -> Optional[str]:
        return self.get('TENCENT_MAP_KEY')
    
    @property
    def deepseek_key(self) -> Optional[str]:
        return self.get('DEEPSEEK_KEY')
    
    @property
    def openai_api_key(self) -> Optional[str]:
        return self.get('OPENAI_API_KEY')
    
    @property
    def qweather_key(self) -> Optional[str]:
        return self.get('QWEATHER_KEY')
    
    @property
    def port(self) -> int:
        return self.get_int('PORT', 5006)
    
    @property
    def debug(self) -> bool:
        return self.get_bool('DEBUG', False)
    
    @property
    def log_level(self) -> str:
        return self.get('LOG_LEVEL', 'INFO')
    
    @property
    def database_path(self) -> Optional[str]:
        return self.get('DATABASE_PATH')
    
    @property
    def base_model_name(self) -> str:
        return self.get('BASE_MODEL_NAME', 'gpt2')
    
    @property
    def model_output_dir(self) -> str:
        return self.get('MODEL_OUTPUT_DIR', './local_models')
    
    @property
    def hf_endpoint(self) -> str:
        return self.get('HF_ENDPOINT', 'https://hf-mirror.com')
    
    @property
    def hf_home(self) -> Optional[str]:
        return self.get('HF_HOME')
    
    @property
    def transformers_cache(self) -> Optional[str]:
        return self.get('TRANSFORMERS_CACHE')
    
    @property
    def api_cache_ttl(self) -> int:
        return self.get_int('API_CACHE_TTL', 3600)
    
    @property
    def enable_cache(self) -> bool:
        return self.get_bool('ENABLE_CACHE', True)
    
    def validate_required_configs(self) -> Dict[str, bool]:
        results = {}
        required_configs = {
            'AMAP_KEY': self.amap_key,
            'DEEPSEEK_KEY': self.deepseek_key
        }
        for config_name, config_value in required_configs.items():
            results[config_name] = config_value is not None and len(config_value.strip()) > 0
        return results
    
    def get_missing_required_configs(self) -> list:
        validation = self.validate_required_configs()
        return [name for name, valid in validation.items() if not valid]
    
    def get_all_configs(self, include_sensitive: bool = False) -> Dict[str, Any]:
        all_configs = {}
        config_keys = [
            'PORT', 'DEBUG', 'LOG_LEVEL', 'BASE_MODEL_NAME', 
            'MODEL_OUTPUT_DIR', 'HF_ENDPOINT', 'API_CACHE_TTL', 
            'ENABLE_CACHE', 'DATABASE_PATH'
        ]
        for key in config_keys:
            all_configs[key] = self.get(key)
        
        if include_sensitive:
            sensitive_keys = [
                'AMAP_KEY', 'BAIDU_MAP_KEY', 'TENCENT_MAP_KEY',
                'DEEPSEEK_KEY', 'OPENAI_API_KEY', 'QWEATHER_KEY'
            ]
            for key in sensitive_keys:
                value = self.get(key)
                if value:
                    masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '***'
                    all_configs[key] = masked
        
        return all_configs

_config_manager_instance: Optional[ConfigManager] = None

def get_config_manager(env_file: Optional[str] = None) -> ConfigManager:
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager(env_file)
    return _config_manager_instance
