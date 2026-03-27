"""Caching system for prefact using diskcache.

This module provides persistent caching functionality to improve performance
by storing scan results, rule configurations, and other computed data.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False

from prefact.config import Config


class Cache:
    """Wrapper for diskcache with additional functionality."""
    
    def __init__(self, cache_dir: Optional[Path] = None, size_limit: int = 1024 * 1024 * 100):  # 100MB
        if not DISKCACHE_AVAILABLE:
            raise ImportError("diskcache is required for caching. Install with: pip install diskcache")
        
        if cache_dir is None:
            cache_dir = Path.home() / ".prefact" / "cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize diskcache
        self.cache = diskcache.Cache(
            str(self.cache_dir),
            size_limit=size_limit,
            eviction_policy='least-recently-used'
        )
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        value = self.cache.get(key, default)
        if value is not default:
            self.stats["hits"] += 1
        else:
            self.stats["misses"] += 1
        return value
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set value in cache."""
        self.cache.set(key, value, expire=expire)
        self.stats["sets"] += 1
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        result = self.cache.delete(key)
        if result:
            self.stats["deletes"] += 1
        return result
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "size": self.cache.volume(),
            "count": len(self.cache),
        }
    
    def close(self) -> None:
        """Close cache."""
        self.cache.close()


class ScanResultCache:
    """Specialized cache for scan results."""
    
    def __init__(self, cache: Cache):
        self.cache = cache
    
    def get_key(
        self, 
        file_path: Path, 
        file_hash: str, 
        rule_ids: tuple[str, ...], 
        config_hash: str
    ) -> str:
        """Generate cache key for scan result."""
        key_parts = [
            "scan",
            str(file_path),
            file_hash,
            ",".join(rule_ids),
            config_hash
        ]
        return ":".join(key_parts)
    
    def get(
        self, 
        file_path: Path, 
        file_hash: str, 
        rule_ids: tuple[str, ...], 
        config_hash: str
    ) -> Optional[Any]:
        """Get cached scan result."""
        key = self.get_key(file_path, file_hash, rule_ids, config_hash)
        return self.cache.get(key)
    
    def set(
        self, 
        file_path: Path, 
        file_hash: str, 
        rule_ids: tuple[str, ...], 
        config_hash: str,
        result: Any,
        expire: int = 3600  # 1 hour
    ) -> None:
        """Cache scan result."""
        key = self.get_key(file_path, file_hash, rule_ids, config_hash)
        self.cache.set(key, result, expire=expire)
    
    def invalidate_file(self, file_path: Path) -> None:
        """Invalidate all cache entries for a file."""
        # This is expensive - in practice, we rely on file hash changes
        pass


class ConfigCache:
    """Cache for rule configurations."""
    
    def __init__(self, cache: Cache):
        self.cache = cache
    
    def get_key(self, config: Config) -> str:
        """Generate cache key for configuration."""
        config_dict = config.to_dict()
        config_str = json.dumps(config_dict, sort_keys=True)
        return f"config:{hashlib.md5(config_str.encode()).hexdigest()}"
    
    def get(self, config: Config) -> Optional[Dict[str, Any]]:
        """Get cached configuration."""
        key = self.get_key(config)
        return self.cache.get(key)
    
    def set(self, config: Config, processed_config: Dict[str, Any]) -> None:
        """Cache processed configuration."""
        key = self.get_key(config)
        self.cache.set(key, processed_config, expire=86400)  # 24 hours


class RuleResultCache:
    """Cache for individual rule results."""
    
    def __init__(self, cache: Cache):
        self.cache = cache
    
    def get_key(
        self, 
        rule_id: str, 
        file_path: Path, 
        file_hash: str, 
        config_hash: str
    ) -> str:
        """Generate cache key for rule result."""
        return f"rule:{rule_id}:{file_path}:{file_hash}:{config_hash}"
    
    def get(
        self, 
        rule_id: str, 
        file_path: Path, 
        file_hash: str, 
        config_hash: str
    ) -> Optional[List[Any]]:
        """Get cached rule result."""
        key = self.get_key(rule_id, file_path, file_hash, config_hash)
        return self.cache.get(key)
    
    def set(
        self, 
        rule_id: str, 
        file_path: Path, 
        file_hash: str, 
        config_hash: str,
        issues: List[Any],
        expire: int = 1800  # 30 minutes
    ) -> None:
        """Cache rule result."""
        key = self.get_key(rule_id, file_path, file_hash, config_hash)
        self.cache.set(key, issues, expire=expire)


class FileHashCache:
    """Cache for file hashes."""
    
    def __init__(self, cache: Cache):
        self.cache = cache
    
    def get_hash(self, file_path: Path) -> Optional[str]:
        """Get cached file hash."""
        key = f"hash:{file_path}"
        mtime = file_path.stat().st_mtime
        
        cached = self.cache.get(key)
        if cached and cached.get("mtime") == mtime:
            return cached.get("hash")
        
        return None
    
    def set_hash(self, file_path: Path, file_hash: str) -> None:
        """Cache file hash with mtime."""
        key = f"hash:{file_path}"
        mtime = file_path.stat().st_mtime
        
        self.cache.set(key, {"hash": file_hash, "mtime": mtime}, expire=86400)


# Global cache instance
_cache: Optional[Cache] = None
_scan_cache: Optional[ScanResultCache] = None
_config_cache: Optional[ConfigCache] = None
_rule_cache: Optional[RuleResultCache] = None
_hash_cache: Optional[FileHashCache] = None


def initialize_cache(config: Config) -> None:
    """Initialize the cache system."""
    global _cache, _scan_cache, _config_cache, _rule_cache, _hash_cache
    
    if not config.get_rule_option("_performance", "cache", True):
        return
    
    cache_dir = config.get_rule_option("_performance", "cache_dir")
    size_limit = config.get_rule_option("_performance", "cache_size", 100 * 1024 * 1024)
    
    _cache = Cache(cache_dir, size_limit)
    _scan_cache = ScanResultCache(_cache)
    _config_cache = ConfigCache(_cache)
    _rule_cache = RuleResultCache(_cache)
    _hash_cache = FileHashCache(_cache)


def get_cache() -> Cache:
    """Get the global cache instance."""
    if _cache is None:
        raise RuntimeError("Cache not initialized. Call initialize_cache() first.")
    return _cache


def get_scan_cache() -> ScanResultCache:
    """Get the scan result cache."""
    if _scan_cache is None:
        raise RuntimeError("Cache not initialized. Call initialize_cache() first.")
    return _scan_cache


def get_config_cache() -> ConfigCache:
    """Get the configuration cache."""
    if _config_cache is None:
        raise RuntimeError("Cache not initialized. Call initialize_cache() first.")
    return _config_cache


def get_rule_cache() -> RuleResultCache:
    """Get the rule result cache."""
    if _rule_cache is None:
        raise RuntimeError("Cache not initialized. Call initialize_cache() first.")
    return _rule_cache


def get_hash_cache() -> FileHashCache:
    """Get the file hash cache."""
    if _hash_cache is None:
        raise RuntimeError("Cache not initialized. Call initialize_cache() first.")
    return _hash_cache


def cleanup_cache() -> None:
    """Clean up cache resources."""
    global _cache, _scan_cache, _config_cache, _rule_cache, _hash_cache
    
    if _cache:
        _cache.close()
    
    _cache = None
    _scan_cache = None
    _config_cache = None
    _rule_cache = None
    _hash_cache = None


# Cache decorators
def cached_result(expire: int = 3600, key_func=None):
    """Decorator to cache function results."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not DISKCACHE_AVAILABLE:
                return func(*args, **kwargs)
            
            cache = get_cache()
            
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}:{hashlib.md5(str(kwargs).encode()).hexdigest()}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, expire=expire)
            
            return result
        
        return wrapper
    return decorator


def cached_file_operation(expire: int = 1800):
    """Decorator to cache file operations."""
    def decorator(func):
        def wrapper(file_path: Path, *args, **kwargs):
            if not DISKCACHE_AVAILABLE:
                return func(file_path, *args, **kwargs)
            
            hash_cache = get_hash_cache()
            
            # Get file hash
            file_hash = hash_cache.get_hash(file_path)
            if file_hash is None:
                # Calculate hash
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                hash_cache.set_hash(file_path, file_hash)
            
            # Generate cache key
            cache = get_cache()
            key = f"{func.__name__}:{file_path}:{file_hash}:{hashlib.md5(str(args).encode()).hexdigest()}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache result
            result = func(file_path, *args, **kwargs)
            cache.set(key, result, expire=expire)
            
            return result
        
        return wrapper
    return decorator


# Cache management utilities
def clear_cache(pattern: Optional[str] = None) -> None:
    """Clear cache entries matching pattern."""
    cache = get_cache()
    
    if pattern:
        # Clear entries matching pattern
        keys_to_delete = []
        for key in cache.cache.iterkeys():
            if pattern in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            cache.delete(key)
    else:
        # Clear all
        cache.clear()


def get_cache_info() -> Dict[str, Any]:
    """Get comprehensive cache information."""
    cache = get_cache()
    stats = cache.get_stats()
    
    # Add additional info
    stats["cache_dir"] = str(cache.cache_dir)
    stats["diskcache_available"] = DISKCACHE_AVAILABLE
    
    # Get cache size on disk
    try:
        total_size = sum(f.stat().st_size for f in cache.cache_dir.rglob('*') if f.is_file())
        stats["disk_size"] = total_size
    except Exception:
        stats["disk_size"] = 0
    
    return stats


# Context manager for cache
class CacheContext:
    """Context manager for cache operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def __enter__(self):
        initialize_cache(self.config)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        cleanup_cache()
