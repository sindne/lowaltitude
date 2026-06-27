import os
from typing import Optional

class Config:
    AMAP_KEY = os.getenv('AMAP_KEY', '03ee0a418d0fa2a2e5eff463bdec23f6')
    DEEPSEEK_KEY = os.getenv('DEEPSEEK_KEY', 'sk-09d148ce6cf34ae68cf87c7a6cb45184')
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_MODEL = "deepseek-chat"
    PORT = int(os.getenv('PORT', 5006))
    HOST = os.getenv('HOST', '0.0.0.0')
    CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', './chroma_db')
    CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'low_altitude_risk')
    KG_STORAGE_PATH = os.getenv('KG_STORAGE_PATH', './knowledge_graph/data')
    TRAINING_DATA_PATH = os.getenv('TRAINING_DATA_PATH', './training/data')
    MODEL_OUTPUT_PATH = os.getenv('MODEL_OUTPUT_PATH', './training/models')
    POSTGIS_HOST = os.getenv('POSTGIS_HOST', 'localhost')
    POSTGIS_PORT = int(os.getenv('POSTGIS_PORT', '5432'))
    POSTGIS_DATABASE = os.getenv('POSTGIS_DATABASE', 'postgres')
    POSTGIS_USER = os.getenv('POSTGIS_USER', 'postgres')
    POSTGIS_PASSWORD = os.getenv('POSTGIS_PASSWORD', '035548')
    CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/app.log')
    
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        return getattr(cls, key, default)
