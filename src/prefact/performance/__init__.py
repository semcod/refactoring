"""Performance optimization modules for pprefact."""

from prefact.performance.cache import (
    Cache,
    CacheContext,
    cleanup_cache,
    clear_cache,
    get_cache,
    get_config_cache,
    get_hash_cache,
    get_rule_cache,
    get_scan_cache,
    initialize_cache,
)
from prefact.performance.parallel import (
    ParallelEngine,
    ParallelScanner,
    ParallelScanTask,
    ScanResultCache,
    get_performance_monitor,
)

__all__ = [
    # Cache
    "Cache",
    "CacheContext",
    "cleanup_cache",
    "clear_cache",
    "get_cache",
    "get_config_cache",
    "get_hash_cache",
    "get_rule_cache",
    "get_scan_cache",
    "initialize_cache",
    # Parallel
    "ParallelEngine",
    "ParallelScanner",
    "ParallelScanTask",
    "ScanResultCache",
    "get_performance_monitor",
]
