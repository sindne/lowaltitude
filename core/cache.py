import time
import threading
from typing import Any, Optional

class CacheManager:
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.cache:
                return None
            value, timestamp = self.cache[key]
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self.lock:
            self.cache[key] = (value, time.time())
    
    def delete(self, key: str) -> None:
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self) -> None:
        with self.lock:
            self.cache.clear()
    
    def cleanup_expired(self) -> None:
        with self.lock:
            current_time = time.time()
            keys_to_delete = [key for key, (_, timestamp) in self.cache.items() if current_time - timestamp > self.ttl]
            for key in keys_to_delete:
                del self.cache[key]

_global_cache = None

def get_global_cache() -> CacheManager:
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache
